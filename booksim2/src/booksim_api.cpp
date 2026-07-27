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
    #include <tuple>
    std::queue<std::tuple<int, int, int>> arrived_packets; // <src, dst, pid>

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
            // CORRECCIÓN: Añadido f->pid a la tupla (src, dst, pid)
            arrived_packets.push({f->src, f->dest, f->pid}); 

            // --- INICIO TFM DEBUG: TRACKING DE PAQUETES ---
            static const char* debug_env = std::getenv("SIM_DEBUG_PIDS");
            if (debug_env && std::string(debug_env) == "1") {
                int receive_time = _time; // _time es variable protegida de TrafficManager
                int latency = receive_time - f->ctime; // f->ctime es el ciclo de inyección
                
                // Imprimimos la traza mágica para que Python la capture
                std::cout << "[TRACK_PID] " << f->pid << "," << f->src << "," 
                          << f->dest << "," << f->ctime << "," << receive_time 
                          << "," << latency << std::endl;
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

bool BookSim_CheckReceived(int& src, int& dst, int& pid) {
    if(g_traffic_manager && !((API_TrafficManager*)g_traffic_manager)->arrived_packets.empty()) {
        auto pkt = ((API_TrafficManager*)g_traffic_manager)->arrived_packets.front();
        ((API_TrafficManager*)g_traffic_manager)->arrived_packets.pop();
        
        src = std::get<0>(pkt);
        dst = std::get<1>(pkt);
        pid = std::get<2>(pkt); // Extraemos el PID
        return true;
    }
    return false;
}
