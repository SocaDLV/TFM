#include "booksim_api.hpp"
#include <iostream>

int main() {
    std::cout << "Inicializando BookSim2 como librería..." << std::endl;
    // Asegúrate de que test.cfg está en la misma carpeta desde la que ejecutas
    BookSim_Initialize("test.cfg"); 

    int src_node = 0;
    int dst_node = 15; // De la esquina superior izq a la inferior der (en un 4x4)
    int packet_size_flits = 5;

    std::cout << "Inyectando paquete de " << packet_size_flits << " flits desde el Nodo " 
              << src_node << " hacia el Nodo " << dst_node << "..." << std::endl;
              
    BookSim_InjectPacket(src_node, dst_node, packet_size_flits);

    int ciclos = 0;
    int arrived_src, arrived_dst;
    bool recibido = false;

    // Lazo cerrado: simulamos la red hasta que el paquete llegue físicamente
    while (!recibido) {
        BookSim_AdvanceCycle();
        ciclos++;
        recibido = BookSim_CheckReceived(arrived_src, arrived_dst);
        
        if(ciclos > 2000) {
            std::cout << "[ERROR] Timeout! El paquete se ha perdido." << std::endl;
            break;
        }
    }

    if (recibido) {
        std::cout << "[ÉXITO] ¡Paquete de " << arrived_src << " a " << arrived_dst 
                  << " recibido exitosamente en " << ciclos << " ciclos de red!" << std::endl;
    }

    return 0;
}
