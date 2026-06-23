import re
import os

# ================= CONFIGURACIÓN DE RUTAS =================
# Ruta relativa desde la carpeta 'middleware' hasta las trazas de LLMSimulator
# IMPORTANTE: Cambia 'nombre_del_archivo.trc' por el nombre real de tu archivo
TRACE_FILE = "../LLMSimulator/build/traces/raw_network_trace_260525_125420.trc"  

# Carpeta de salida y archivo final para BookSim2
OUTPUT_DIR = "booksim2_output_files"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "booksim_trace.txt")

# ================= PARÁMETROS DE HARDWARE =================
NETWORK_FREQ_GHZ = 1.0  # 1 GHz -> 1 Ciclo = 1 nanosegundo
FLIT_SIZE_BYTES = 32    # Tamaño de la unidad mínima de red (ej. 32 Bytes por flit)
# ==========================================================

def parse_and_convert():
    print(f"Leyendo y procesando: {TRACE_FILE}...")
    packets = []
    
    # Regex para extraer los datos de tu traza de LLMSimulator
    regex = re.compile(r'TIME_NS:(\d+).*?SRC:(\d+) DST:(\d+) BYTES:(\d+)')
    
    try:
        with open(TRACE_FILE, 'r') as f:
            for line in f:
                match = regex.search(line)
                if match:
                    time_ns = int(match.group(1))
                    src = int(match.group(2))
                    dst = int(match.group(3))
                    bytes_sent = int(match.group(4))
                    
                    # Conversión a dominio BookSim
                    # 1. Convertir NS a Ciclos
                    cycle = int(time_ns * NETWORK_FREQ_GHZ)
                    
                    # 2. Convertir Bytes a Flits (redondeando hacia arriba)
                    flits = (bytes_sent + FLIT_SIZE_BYTES - 1) // FLIT_SIZE_BYTES
                    
                    packets.append((cycle, src, dst, flits))
    except FileNotFoundError:
        print(f"\n[ERROR] No se encontró el archivo: {TRACE_FILE}")
        print("Asegúrate de haber puesto el nombre exacto del .trc en la variable TRACE_FILE.")
        return

    if not packets:
        print("\n[ERROR] No se encontraron datos válidos. Revisa el regex o el archivo.")
        return

    # ¡VITAL! Ordenar cronológicamente (por ciclo)
    print("Ordenando paquetes cronológicamente...")
    packets.sort(key=lambda x: x[0])

    # Crear la carpeta de salida si no existe
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Carpeta '{OUTPUT_DIR}' creada.")

    # Escribir el archivo final para BookSim2
    print(f"Escribiendo {len(packets)} paquetes en {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        for p in packets:
            # Formato estricto para BookSim2: Ciclo Origen Destino Numero_de_Flits
            f.write(f"{p[0]} {p[1]} {p[2]} {p[3]}\n")

if __name__ == "__main__":
    parse_and_convert()
    print("\n¡Transformación completada con éxito!")
