import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def plot_gantt(df_subset, title, filename, folder):
    """Función auxiliar para generar y guardar el gráfico de Gantt."""
    if df_subset.empty:
        print(f"⚠️ Aviso: No hay suficientes datos para generar '{title}'.")
        return

    # Ordenar estrictamente por PID para que la ventana temporal sea perfecta
    df_subset = df_subset.sort_values(by='PID', ascending=False)

    fig, ax = plt.subplots(figsize=(12, 8))

    bars = ax.barh(df_subset['PID'].astype(str), df_subset['Latency'], 
                   left=df_subset['Inject_Cycle'], 
                   color='royalblue', edgecolor='black', alpha=0.8)

    # Añadir etiquetas (Src -> Dst)
    for bar, src, dst in zip(bars, df_subset['Source'], df_subset['Dest']):
        ax.text(bar.get_x() + bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                f"S{src}→D{dst}", va='center', ha='left', fontsize=9)

    ax.set_xlabel("Ciclos de Reloj (BookSim2)", fontsize=12)
    ax.set_ylabel("Packet ID (PID Secuencial)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.grid(axis='x', linestyle='--', alpha=0.6)

    plt.tight_layout()
    output_png = os.path.join(folder, filename)
    plt.savefig(output_png, dpi=300)
    plt.close(fig)
    print(f"✅ Generado: {output_png}")

def get_pid_window(df, threshold, samples):
    """
    Busca el primer paquete cuya latencia supere el 'threshold'.
    Devuelve un DataFrame con una "foto" secuencial de PIDs centrada en él.
    """
    # Buscar los paquetes que superen el umbral
    target_pkts = df[df['Latency'] >= threshold]
    
    if target_pkts.empty:
        return pd.DataFrame() # No se alcanzó este nivel de congestión
        
    # Cogemos el PID del primero que rompe el umbral
    target_pid = target_pkts.iloc[0]['PID']
    
    # Calculamos la ventana (mitad por debajo, mitad por encima)
    half_window = samples // 2
    min_pid = target_pid - half_window
    max_pid = target_pid + half_window
    
    # Filtramos la "foto" secuencial
    window_df = df[(df['PID'] >= min_pid) & (df['PID'] <= max_pid)]
    
    # Por si hay huecos, nos aseguramos de limitar exactamente al número de samples
    return window_df.head(samples)

def main():
    parser = argparse.ArgumentParser(description="Genera Gráficos de Gantt de Paquetes en Vuelo (TFM)")
    parser.add_argument("folder", type=str, help="Ruta a la carpeta de resultados")
    parser.add_argument("--samples", type=int, default=50, help="Número de paquetes (ventana) por gráfico")
    args = parser.parse_args()

    csv_path = os.path.join(args.folder, "packet_tracking_debug.csv")
    if not os.path.exists(csv_path):
        print(f"❌ Error: No se encontró {csv_path}.")
        return

    df = pd.read_csv(csv_path)
    df['Latency'] = pd.to_numeric(df['Latency'])
    df['PID'] = pd.to_numeric(df['PID'])

    # El DataFrame maestro, ordenado secuencialmente por el simulador (PID)
    df_sorted = df.sort_values(by='PID', ascending=True)

    print(f"📊 Analizando la línea de tiempo de {len(df)} paquetes para {args.folder}...")

    # --- GRÁFICO 1: Fase Libre (La cabeza del pelotón) ---
    df_base = df_sorted.head(args.samples)
    plot_gantt(df_base, 
               f"1. Fase Libre (Flujo ideal) - {args.samples} PIDs secuenciales", 
               "gantt_1_fase_libre.png", 
               args.folder)

    # --- GRÁFICO 2: Congestión Media (Ventana alrededor de Latencia > 1500) ---
    df_media = get_pid_window(df_sorted, threshold=1500, samples=args.samples)
    if not df_media.empty:
        target_pid = df_media.iloc[len(df_media)//2]['PID'] # PID central para el título
        plot_gantt(df_media, 
                   f"2. Inicio de Congestión (Entorno al PID {target_pid})", 
                   "gantt_2_congestion_media.png", 
                   args.folder)
    else:
        print("ℹ️ No se detectó congestión > 1500 ciclos en esta simulación.")

    # --- GRÁFICO 3: Embotellamiento Crítico (Ventana alrededor de Latencia > 2000) ---
    df_critica = get_pid_window(df_sorted, threshold=2000, samples=args.samples)
    if not df_critica.empty:
        target_pid = df_critica.iloc[len(df_critica)//2]['PID']
        plot_gantt(df_critica, 
                   f"3. Embotellamiento Crítico (Entorno al PID {target_pid})", 
                   "gantt_3_congestion_critica.png", 
                   args.folder)
    else:
        print("ℹ️ No se detectó congestión crítica > 2000 ciclos en esta simulación.")

if __name__ == "__main__":
    main()