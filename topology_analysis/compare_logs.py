import re
import os
import matplotlib.pyplot as plt
import numpy as np

# ================= CONFIGURACIÓN =================
# Rutas relativas desde TFM/topology_analysis/ a los logs en TFMresults/
LOG_DIR = "../booksim2/src/TFMresults/"

LOG_FILES = {
    "Malla 1D (Baseline)": os.path.join(LOG_DIR, "dia2_exec2.txt"),
    "Malla 2D (4x2 Adaptable)": os.path.join(LOG_DIR, "dia2_exec1.txt")
}
# =================================================

def extract_metrics(filepath):
    """Extrae las métricas clave de la sección final de estadísticas de BookSim2."""
    metrics = {
        "Packet latency": None,
        "Network latency": None,
        "Accepted flit rate": None,
        "Hops": None
    }
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
            # Buscar desde el final hacia atrás la sección de Overall Stats
            in_overall_stats = False
            for line in lines:
                if "====== Overall Traffic Statistics ======" in line:
                    in_overall_stats = True
                    
                if in_overall_stats:
                    # CORRECCIÓN: Usamos \S+ para capturar notación científica (ej. 1.1186e+06)
                    if "Packet latency average" in line and metrics["Packet latency"] is None:
                        match = re.search(r'average = (\S+)', line)
                        if match and match.group(1).lower() not in ['nan', '-nan']:
                            metrics["Packet latency"] = float(match.group(1))
                            
                    elif "Network latency average" in line and metrics["Network latency"] is None:
                        match = re.search(r'average = (\S+)', line)
                        if match and match.group(1).lower() not in ['nan', '-nan']:
                            metrics["Network latency"] = float(match.group(1))
                            
                    elif "Accepted flit rate average" in line and metrics["Accepted flit rate"] is None:
                        match = re.search(r'average = (\S+)', line)
                        if match and match.group(1).lower() not in ['nan', '-nan']:
                            metrics["Accepted flit rate"] = float(match.group(1))
                            
                    elif "Hops average" in line and metrics["Hops"] is None:
                        match = re.search(r'average = (\S+)', line)
                        if match and match.group(1).lower() not in ['nan', '-nan']:
                            metrics["Hops"] = float(match.group(1))
    except FileNotFoundError:
        print(f"[ERROR] No se encontró el archivo: {filepath}")
        return None

    return metrics

def plot_latency_comparison(results):
    """Genera un gráfico de barras agrupadas comparando las latencias."""
    labels = list(results.keys())
    packet_lats = [results[label].get("Packet latency", 0) for label in labels]
    network_lats = [results[label].get("Network latency", 0) for label in labels]

    x = np.arange(len(labels))
    width = 0.35

    # Estilo académico (más limpio)
    plt.style.use('ggplot') 
    fig, ax = plt.subplots(figsize=(10, 6))
    
    rects1 = ax.bar(x - width/2, network_lats, width, label='Network Latency (Tránsito)', color='#2ca02c')
    rects2 = ax.bar(x + width/2, packet_lats, width, label='Packet Latency (Total con Colas)', color='#d62728')

    ax.set_ylabel('Ciclos (Escala Logarítmica)', fontweight='bold')
    ax.set_title('Impacto de la Congestión: Tránsito Físico vs. Colas de Inyección', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontweight='bold', fontsize=11)
    ax.legend()
    
    # Escala logarítmica para ver bien ambas barras
    ax.set_yscale('log')
    
    # Añadir valores numéricos encima de las barras adaptado a números grandes
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            if height > 0:
                # Usar formato con comas para que 1118600 se vea como 1,118,600
                ax.annotate(f'{height:,.0f}',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3), 
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)
    autolabel(rects1)
    autolabel(rects2)

    fig.tight_layout()
    plt.savefig("grafica_latencia.png", dpi=300)
    print("-> Gráfica guardada como 'grafica_latencia.png'")

def plot_throughput_comparison(results):
    """Genera un gráfico de barras para el Throughput (Flit Rate)."""
    labels = list(results.keys())
    throughput = [results[label].get("Accepted flit rate", 0) for label in labels]

    fig, ax = plt.subplots(figsize=(8, 5))
    rects = ax.bar(labels, throughput, color='#1f77b4', width=0.4)

    ax.set_ylabel('Accepted Flit Rate (Flits/Ciclo/Nodo)', fontweight='bold')
    ax.set_title('Rendimiento de la Red (Throughput Mínimo Garantizado)', fontsize=14)
    
    # El máximo teórico suele ser 1.0
    max_ylim = max(throughput) * 1.5 if max(throughput) > 0 else 1.0
    ax.set_ylim(0, max_ylim) 
    
    ax.set_xticklabels(labels, fontweight='bold', fontsize=11)

    # Valores en las barras
    for rect in rects:
        height = rect.get_height()
        if height > 0:
            ax.annotate(f'{height:.4f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')

    fig.tight_layout()
    plt.savefig("grafica_throughput.png", dpi=300)
    print("-> Gráfica guardada como 'grafica_throughput.png'")

if __name__ == "__main__":
    extracted_data = {}
    print("--- Extrayendo métricas de BookSim2 ---")
    
    for name, filepath in LOG_FILES.items():
        print(f"\nAnalizando {name} ({filepath})...")
        metrics = extract_metrics(filepath)
        if metrics:
            if metrics["Packet latency"] is None:
                print("  [AVISO] No se encontró 'Packet latency' válida. Posible colapso de red o log incompleto.")
            else:
                extracted_data[name] = metrics
                print(f"  Packet Latency: {metrics['Packet latency']:,.2f}")
                print(f"  Network Latency: {metrics['Network latency']:,.2f}")
                print(f"  Throughput: {metrics['Accepted flit rate']:.4f}")
                print(f"  Saltos (Hops): {metrics['Hops']:.2f}")

    print("\n--- Generando gráficas ---")
    if len(extracted_data) > 0:
        plot_latency_comparison(extracted_data)
        plot_throughput_comparison(extracted_data)
        print("¡Proceso completado con éxito!")
    else:
        print("Error: No se encontraron datos válidos en los logs especificados para generar gráficas.")
