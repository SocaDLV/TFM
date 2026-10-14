import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def plot_gantt(df_subset, title, filename, folder):
    """Función auxiliar para generar y guardar el gráfico de Gantt con dos tramos por barra."""
    if df_subset.empty:
        print(f"⚠️ Aviso: No hay suficientes datos para generar '{title}'.")
        return

    # Ordenar por PID descendente para que el menor PID aparezca arriba en el eje Y
    df_subset = df_subset.sort_values(by='PID', ascending=False)

    fig, ax = plt.subplots(figsize=(14, 9))

    # Tramo 1: Espera en cola de inyección / NIC Queueing [Creation_Cycle -> Inject_Cycle]
    bars_q = ax.barh(df_subset['PID'].astype(str), df_subset['Queueing_Delay'], 
                     left=df_subset['Creation_Cycle'], 
                     color='#ff7f0e', edgecolor='black', linewidth=0.3, alpha=0.85,
                     label='Espera en cola (NIC Queueing)')

    # Tramo 2: Vuelo real en la NoC [Inject_Cycle -> Receive_Cycle]
    bars_net = ax.barh(df_subset['PID'].astype(str), df_subset['Network_Latency'], 
                       left=df_subset['Inject_Cycle'], 
                       color='#1f77b4', edgecolor='black', linewidth=0.3, alpha=0.85,
                       label='Vuelo en Red (NoC Flight)')

    # Cálculo dinámico del margen para evitar solapamiento de etiquetas
    min_x = df_subset['Creation_Cycle'].min()
    max_x = df_subset['Receive_Cycle'].max()
    x_span = max(1.0, max_x - min_x)
    text_offset = max(1.0, x_span * 0.008)

    # Añadir etiquetas detalladas: S{src}→D{dst} (X flits / Y B)
    for _, row in df_subset.iterrows():
        y_pos = str(int(row['PID']))
        x_pos = row['Receive_Cycle'] + text_offset
        src = int(row['Source'])
        dst = int(row['Dest'])
        flits = int(row['Num_Flits'])
        bytes_val = int(row['Size_Bytes'])
        
        ax.text(x_pos, y_pos, 
                f"S{src}→D{dst} ({flits} flits / {bytes_val} B)", 
                va='center', ha='left', fontsize=8, color='#111111')

    ax.set_xlabel("Ciclos de Reloj (BookSim2)", fontsize=12)
    ax.set_ylabel("Packet ID (PID Secuencial)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    ax.legend(loc='upper right', framealpha=0.9, fontsize=10)

    # Margen extra a la derecha para que quepan las etiquetas de texto
    ax.set_xlim(left=max(0, min_x - x_span * 0.02), right=max_x + x_span * 0.25)

    plt.tight_layout()
    output_png = os.path.join(folder, filename)
    plt.savefig(output_png, dpi=300)
    plt.close(fig)
    print(f"✅ Generado: {output_png}")

def get_pid_window(df, threshold, samples):
    """
    Busca el primer paquete cuya latencia supere el 'threshold'.
    Devuelve un DataFrame con una 'foto' secuencial de PIDs centrada en él.
    """
    lat_col = 'Total_Latency' if 'Total_Latency' in df.columns else 'Latency'
    target_pkts = df[df[lat_col] >= threshold]
    
    if target_pkts.empty:
        return pd.DataFrame() # No se alcanzó este nivel de congestión
        
    target_pid = target_pkts.iloc[0]['PID']
    
    half_window = samples // 2
    min_pid = target_pid - half_window
    max_pid = target_pid + half_window
    
    window_df = df[(df['PID'] >= min_pid) & (df['PID'] <= max_pid)]
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

    # Compatibilidad con CSVs antiguos si carecen de las nuevas columnas
    if 'Total_Latency' not in df.columns and 'Latency' in df.columns:
        df['Total_Latency'] = df['Latency']
        df['Network_Latency'] = df['Latency']
        df['Queueing_Delay'] = 0
        df['Creation_Cycle'] = df['Inject_Cycle']
        df['Num_Flits'] = 1
        df['Size_Bytes'] = 32

    # Conversión numérica de columnas clave
    cols_to_numeric = ['PID', 'Source', 'Dest', 'Creation_Cycle', 'Inject_Cycle', 
                       'Receive_Cycle', 'Total_Latency', 'Network_Latency', 
                       'Queueing_Delay', 'Num_Flits', 'Size_Bytes']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

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