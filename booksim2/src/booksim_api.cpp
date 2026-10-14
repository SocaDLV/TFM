#include "booksim_api.hpp"
#include "booksim.hpp"
#include "booksim_config.hpp"
#include "network.hpp"
#include "trafficmanager.hpp"
#include "routefunc.hpp"
#include "flit.hpp"
#include <queue>
#include <iostream>
#include <sstream>

// =========================================================================
// VARIABLES GLOBALES (Reemplazando a main.cpp para poder compilar sin él)
// =========================================================================
bool gPrintActivity = false;
int gK = 0;
int gN = 0;
int gC = 0;
int gNodes = 0;
bool gTrace = false;
std::ostream * gWatchOut = nullptr;

class API_TrafficManager : public TrafficManager {
public:
    std::queue<BookSimPacketInfo> arrived_packets;

    API_TrafficManager(const Configuration &config, const vector<Network *> & net)
        : TrafficManager(config, net) {}

    // Exponemos el método protegido _Step()
    void Step() {
        _Step();
    }

    // Inyección manual directa a los buffers de BookSim2
    int Inject(int src, int dst, int size_in_flits) {
      int pid = _cur_pid++; // Booksim ya lleva este contador
      int time = _time;

        for(int i = 0; i < size_in_flits; ++i) {
            Flit *f = Flit::New();
            f->id = _cur_id++;
            f->pid = pid;
            f->watch = false;
            f->subnetwork = 0;
            f->src = src;
            f->ctime = time;
            f->record = false;
            f->cl = 0; // Usamos siempre la Traffic Class 0 por defecto
            f->dest = dst;
            f->type = Flit::ANY_TYPE;

            f->head = (i == 0);
            f->tail = (i == size_in_flits - 1);
            f->vc = -1; // El enrutador de origen le asignará el VC

            // ¡LA MAGIA DEL BOOKKEEPING ESTÁ AQUÍ!
            // Le decimos a BookSim2 que este Flit es oficial y está en vuelo
            _total_in_flight_flits[f->cl].insert(std::make_pair(f->id, f));

            // Inyectamos directamente en la cola de paquetes parciales
            _partial_packets[src][0].push_back(f);
        }
        return pid;
    }

    // Interceptamos los flits cuando se retiran de la red al llegar a destino
    virtual void _RetireFlit(Flit *f, int dest) override {
        if (f->tail) { // Si es el último flit del paquete, registramos la llegada
            Flit * head = nullptr;
            if (f->head) {
                head = f;
            } else {
                auto iter = _retired_packets[f->cl].find(f->pid);
                if (iter != _retired_packets[f->cl].end()) {
                    head = iter->second;
                }
            }

            int pid = f->pid;
            int src = f->src;
            int dst = dest;
            int ctime = head ? head->ctime : f->ctime;
            int itime = head ? head->itime : f->itime;
            int atime = _time; // Llegada del tail flit
            int total_latency = atime - ctime;
            int network_latency = atime - itime;
            int queueing_delay = itime - ctime;
            int num_flits = head ? (f->id - head->id + 1) : 1;
            int size_bytes = num_flits * 32;

            BookSimPacketInfo pkt;
            pkt.pid = pid;
            pkt.src = src;
            pkt.dst = dst;
            pkt.ctime = ctime;
            pkt.itime = itime;
            pkt.atime = atime;
            pkt.total_latency = total_latency;
            pkt.network_latency = network_latency;
            pkt.queueing_delay = queueing_delay;
            pkt.num_flits = num_flits;
            pkt.size_bytes = size_bytes;

            arrived_packets.push(pkt);

            // --- INICIO TFM DEBUG: TRACKING DE PAQUETES ---
            static const char* debug_env = std::getenv("SIM_DEBUG_PIDS");
            if (debug_env && std::string(debug_env) == "1") {
                // Formato de exportación: PID,Source,Dest,Creation_Cycle,Inject_Cycle,Receive_Cycle,Total_Latency,Network_Latency,Queueing_Delay,Num_Flits,Size_Bytes
                std::cout << "[TRACK_PID] " << pid << "," << src << "," << dst << "," 
                          << ctime << "," << itime << "," << atime << "," 
                          << total_latency << "," << network_latency << "," << queueing_delay << ","
                          << num_flits << "," << size_bytes << std::endl;
            }
            // --- FIN TFM DEBUG ---
        }
        TrafficManager::_RetireFlit(f, dest);
    }
};

static API_TrafficManager* g_traffic_manager = nullptr;
static vector<Network *> g_networks;

// Implementación de las funciones esperadas por globals.hpp
int GetSimTime() {
    return g_traffic_manager ? g_traffic_manager->getTime() : 0;
}

Stats * GetStats(const std::string & name) {
    return g_traffic_manager ? g_traffic_manager->getStats(name) : nullptr;
}

// =========================================================================
// IMPLEMENTACIÓN DE LA API
// =========================================================================

void BookSim_Initialize(const char* config_file) {
    BookSimConfig config;
    const char* argv[] = {"booksim", config_file};
    ParseArgs(&config, 2, (char**)argv);

    InitializeRoutingMap(config);

    int subnets = config.GetInt("subnets");
    g_networks.resize(subnets);
    for (int i = 0; i < subnets; ++i) {
        ostringstream name;
        name << "network_" << i;
        g_networks[i] = Network::New(config, name.str());
    }

    g_traffic_manager = new API_TrafficManager(config, g_networks);
}

int BookSim_InjectPacket(int src, int dst, int size_in_flits) {
    if(g_traffic_manager) {
        return ((API_TrafficManager*)g_traffic_manager)->Inject(src, dst, size_in_flits);
    }
    return -1;
}

void BookSim_AdvanceCycle() {
    if(g_traffic_manager) {
        g_traffic_manager->Step();
    }
}

bool BookSim_CheckReceived(BookSimPacketInfo& info) {
    if(g_traffic_manager && !((API_TrafficManager*)g_traffic_manager)->arrived_packets.empty()) {
        info = ((API_TrafficManager*)g_traffic_manager)->arrived_packets.front();
        ((API_TrafficManager*)g_traffic_manager)->arrived_packets.pop();
        return true;
    }
    return false;
}

bool BookSim_CheckReceived(int& src, int& dst, int& pid) {
    BookSimPacketInfo info;
    if (BookSim_CheckReceived(info)) {
        src = info.src;
        dst = info.dst;
        pid = info.pid;
        return true;
    }
    return false;
}

