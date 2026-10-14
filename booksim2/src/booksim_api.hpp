#ifndef BOOKSIM_API_HPP
#define BOOKSIM_API_HPP

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

#endif // BOOKSIM_API_HPP

