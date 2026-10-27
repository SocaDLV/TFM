#ifndef BOOKSIM_API_HPP
#define BOOKSIM_API_HPP

#include <string>

struct BookSimPacketInfo {
    int pid;
    int src;
    int dst;
    int ctime;
    int itime;
    int atime;
    int total_latency;
    int network_latency;
    int queueing_delay;
    int num_flits;
    int size_bytes;
    double avg_flit_lat;
    double throughput;
    std::string op_type;
    int op_idx;
    double op_start_ns;
    double op_end_ns;
};

// Inicializa la topología de red usando un archivo de configuración de BookSim2.
void BookSim_Initialize(const char* config_file);

// Inyecta un paquete físico en la red, dividiéndolo en "flits".
int BookSim_InjectPacket(int src, int dst, int size_in_flits);

// Avanza la simulación de red exactamente 1 ciclo de reloj.
void BookSim_AdvanceCycle();

// Comprueba si algún paquete ha llegado a su destino final en este ciclo.
// Retorna true si ha llegado un paquete y rellena 'src', 'dst' y 'pid'.
bool BookSim_CheckReceived(int& src, int& dst, int& pid);

// Sobrecarga extendida que devuelve toda la información de tracking del paquete.
bool BookSim_CheckReceived(BookSimPacketInfo& info);

// Inicia una operación de red (Scatter o Gather) fijando el contexto de trazado
void BookSim_StartOperation(const std::string& op_type, int op_idx, double op_start_ns);

// Finaliza la operación de red, fija el tiempo final en ns y emite los registros [TRACK_PID]
void BookSim_FinishOperation(double op_end_ns);

#endif // BOOKSIM_API_HPP

