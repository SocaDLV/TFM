import os
import argparse
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def render_gantt_page(df_page, title, output_png, is_summary=False):
    """
    Renderiza un diagrama de Gantt de alta resolución para un lote de paquetes (típicamente 50).
    Incluye:
      - Desglose dual: Cola NIC (naranja) y Tránsito en Red (azul).
      - Etiqueta enriquecida: S{src}→D{dst} (flits/B) | Lat.Mitja: {avg_lat}c | Prod: {prod} flits/c.
      - Bandas de fondo coloreadas (axhspan) por Operación de Red (Scatter / Gather).
      - Línea divisoria entre operaciones consecutivas.
      - Badge destacado a la derecha con el nombre de la operación y rango de nanosegundos.
    """
    if df_page.empty:
        return

    # Ordenar por PID ascendente internamente
    df_page = df_page.sort_values(by='PID', ascending=True).copy().reset_index(drop=True)
    n_pkts = len(df_page)

    # Posiciones en eje Y: el menor PID arriba (y = n_pkts - 1) y el mayor abajo (y = 0)
    y_pos = np.arange(n_pkts)[::-1]
    df_page['y_pos'] = y_pos

    fig, ax = plt.subplots(figsize=(16, max(7, n_pkts * 0.22 + 2)))

    # Límites temporales
    min_x = df_page['Creation_Cycle'].min()
    max_x = df_page['Receive_Cycle'].max()
    x_span = max(1.0, max_x - min_x)
    text_offset = max(1.0, x_span * 0.008)

    # 1. ZONAS SOMBREADAS POR OPERACIÓN DE RED (Scatter / Gather)
    # Detectamos bloques contiguos de la misma operación (Op_Type y Op_Idx)
    df_page['op_key'] = df_page['Op_Type'].astype(str) + "_" + df_page['Op_Idx'].astype(str)
    
    op_runs = []
    start_idx = 0
    for i in range(1, n_pkts + 1):
        if i == n_pkts or df_page.loc[i, 'op_key'] != df_page.loc[start_idx, 'op_key']:
            op_runs.append((start_idx, i - 1))
            start_idx = i

    scatter_color = '#e3f2fd'  # Azul suave
    gather_color = '#f3e5f5'   # Violeta suave
    div_line_color = '#555555'

    for run_idx, (r_start, r_end) in enumerate(op_runs):
        sub = df_page.iloc[r_start:r_end + 1]
        y_top = sub['y_pos'].max() + 0.5
        y_bottom = sub['y_pos'].min() - 0.5
        y_center = (y_top + y_bottom) / 2.0

        op_type = str(sub.iloc[0]['Op_Type']) if 'Op_Type' in sub.columns else 'Scatter'
        op_idx = int(sub.iloc[0]['Op_Idx']) if 'Op_Idx' in sub.columns else 1
        op_start_ns = float(sub.iloc[0]['Op_Start_NS']) if 'Op_Start_NS' in sub.columns else 0.0
        op_end_ns = float(sub.iloc[0]['Op_End_NS']) if 'Op_End_NS' in sub.columns else 0.0

        is_scatter = "scatter" in op_type.lower()
        bg_color = scatter_color if is_scatter else gather_color
        badge_bg = '#bbdefb' if is_scatter else '#e1bee7'
        badge_edge = '#1976d2' if is_scatter else '#8e24aa'

        # Sombrear fondo de la zona
        ax.axhspan(y_bottom, y_top, facecolor=bg_color, alpha=0.45, zorder=0)

        # Línea divisoria inferior si hay otra operación a continuación
        if run_idx < len(op_runs) - 1:
            ax.axhline(y=y_bottom, color=div_line_color, linestyle='--', linewidth=1.1, alpha=0.75, zorder=2)

        # Badge lateral a la derecha
        badge_x = max_x + x_span * 0.44
        badge_str = f"{op_type} Nº{op_idx}\nNS {int(round(op_start_ns))} - {int(round(op_end_ns))}"
        ax.text(badge_x, y_center, badge_str,
                va='center', ha='left', fontsize=9.5, fontweight='bold',
                color='#0d233a',
                bbox=dict(boxstyle='round,pad=0.55', facecolor=badge_bg, edgecolor=badge_edge, linewidth=1.3, alpha=0.92),
                zorder=5)

    # 2. BARRAS DE GANTT (Cola NIC y Tránsito NoC)
    bars_q = ax.barh(y_pos, df_page['Queueing_Delay'],
                     left=df_page['Creation_Cycle'],
                     color='#ff7f0e', edgecolor='#444444', linewidth=0.35, height=0.68, alpha=0.88,
                     label='Espera en cola NIC (Queueing Delay)', zorder=3)

    bars_net = ax.barh(y_pos, df_page['Network_Latency'],
                       left=df_page['Inject_Cycle'],
                       color='#1f77b4', edgecolor='#444444', linewidth=0.35, height=0.68, alpha=0.88,
                       label='Vuelo en Red BookSim2 (Flight Time)', zorder=3)

    # 3. ETIQUETA ENRIQUECIDA AL LADO DE CADA PAQUETE
    for _, row in df_page.iterrows():
        y_val = row['y_pos']
        x_val = row['Receive_Cycle'] + text_offset
        src = int(row['Source'])
        dst = int(row['Dest'])
        flits = int(row['Num_Flits'])
        bytes_val = int(row['Size_Bytes'])
        avg_flit_lat = float(row.get('Avg_Flit_Latency', row.get('Total_Latency', 0.0)))
        prod = float(row.get('Throughput', 0.0))
        op_start_ns = float(row.get('Op_Start_NS', 0.0))
        c_cycle = float(row.get('Creation_Cycle', 0.0))
        g_start_ns = op_start_ns + (row['Inject_Cycle'] - c_cycle)
        g_end_ns = op_start_ns + (row['Receive_Cycle'] - c_cycle)

        label_txt = f"S{src}→D{dst} ({flits} flits / {bytes_val}B) | Lat.Mitja: {avg_flit_lat:.1f}c | Prod: {prod:.3f} flits/c | NS: {g_start_ns:.0f}-{g_end_ns:.0f}"
        ax.text(x_val, y_val, label_txt, va='center', ha='left', fontsize=7.8, color='#111111', zorder=4)

    # Configuración de Ejes y Estética
    ax.set_yticks(y_pos)
    ax.set_yticklabels([str(int(pid)) for pid in df_page['PID']], fontsize=8.5)
    ax.set_ylim(-0.7, n_pkts - 0.3)

    ax.set_xlabel("Ciclos de Reloj (BookSim2)", fontsize=12, fontweight='semibold')
    ax.set_ylabel("Packet ID (PID Secuencial)", fontsize=12, fontweight='semibold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=56)
    ax.grid(axis='x', linestyle=':', alpha=0.6, zorder=1)

    # Eje Secundario Superior: Tiempo Global LLM en Nanosegundos
    ref_row = df_page.iloc[0]
    ref_start_ns = float(ref_row.get('Op_Start_NS', 0.0))
    ref_start_cycle = float(ref_row.get('Creation_Cycle', 0.0))

    secax = ax.secondary_xaxis('top', functions=(
        lambda c: ref_start_ns + (c - ref_start_cycle),
        lambda ns: ref_start_cycle + (ns - ref_start_ns)
    ))
    secax.set_xlabel("Tiempo Global LLM (ns)", fontsize=11, fontweight='semibold', labelpad=7)
    secax.tick_params(labelsize=8.5)

    ax.legend(loc='lower left', bbox_to_anchor=(0.0, 1.13), ncol=2, framealpha=0.95, fontsize=10)

    # Margen derecho suficiente para etiquetas y badges de operación
    ax.set_xlim(left=max(0, min_x - x_span * 0.02), right=max_x + x_span * 0.72)

    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"✅ Generado: {output_png}")


def get_pid_window(df, threshold, samples):
    """
    Busca el primer paquete cuya latencia supere 'threshold' y devuelve
    una ventana de 'samples' paquetes centrada en él.
    """
    lat_col = 'Total_Latency' if 'Total_Latency' in df.columns else 'Latency'
    target_pkts = df[df[lat_col] >= threshold]
    if target_pkts.empty:
        return pd.DataFrame()

    target_pid = target_pkts.iloc[0]['PID']
    half = samples // 2
    min_pid = target_pid - half
    max_pid = target_pid + half
    window = df[(df['PID'] >= min_pid) & (df['PID'] <= max_pid)]
    return window.head(samples)


def main():
    parser = argparse.ArgumentParser(description="Visualizador de Trazado de Paquetes y Flits en BookSim2 (TFM)")
    parser.add_argument("folder", type=str, help="Ruta a la carpeta de resultados de la simulación")
    parser.add_argument("--samples", type=int, default=50, help="Número de paquetes por página (por defecto: 50)")
    parser.add_argument("--max_pages", type=int, default=30, help="Máximo de páginas a generar en gantt/ (por defecto: 30, use 0 para todas)")
    parser.add_argument("--all_iters", action="store_true", help="Si se especifica, incluye todas las iteraciones en lugar de filtrar la última")
    args = parser.parse_args()

    csv_path = os.path.join(args.folder, "packet_tracking_debug.csv")
    if not os.path.exists(csv_path):
        print(f"❌ Error: No se encontró el archivo {csv_path}.")
        return

    print(f"📖 Cargando trazas de red desde: {csv_path}...")
    df = pd.read_csv(csv_path)

    if df.empty:
        print("⚠️ El archivo de tracking está vacío.")
        return

    # Compatibilidad con CSVs antiguos
    if 'Total_Latency' not in df.columns and 'Latency' in df.columns:
        df['Total_Latency'] = df['Latency']
        df['Network_Latency'] = df['Latency']
        df['Queueing_Delay'] = 0
        df['Creation_Cycle'] = df['Inject_Cycle']
        df['Num_Flits'] = 9
        df['Size_Bytes'] = 288

    if 'Avg_Flit_Latency' not in df.columns:
        df['Avg_Flit_Latency'] = df['Total_Latency']
    if 'Throughput' not in df.columns:
        df['Throughput'] = 0.0
    if 'Op_Type' not in df.columns:
        df['Op_Type'] = 'Scatter'
    if 'Op_Idx' not in df.columns:
        df['Op_Idx'] = 1
    if 'Op_Start_NS' not in df.columns:
        df['Op_Start_NS'] = 0.0
    if 'Op_End_NS' not in df.columns:
        df['Op_End_NS'] = 0.0

    # Conversión numérica
    num_cols = ['PID', 'Source', 'Dest', 'Creation_Cycle', 'Inject_Cycle',
                'Receive_Cycle', 'Total_Latency', 'Network_Latency',
                'Queueing_Delay', 'Num_Flits', 'Size_Bytes',
                'Avg_Flit_Latency', 'Throughput', 'Op_Idx', 'Op_Start_NS', 'Op_End_NS']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 1. FILTRO DE ÚLTIMA ITERACIÓN POR DEFECTO
    total_raw_packets = len(df)
    if not args.all_iters:
        # Detectar reseteo temporal en Op_Start_NS o Creation_Cycle
        if 'Op_Start_NS' in df.columns and (df['Op_Start_NS'].diff() < 0).any():
            drops = df['Op_Start_NS'].diff() < 0
            last_reset = drops[drops].index[-1]
            df = df.loc[last_reset:].copy()
            print(f"🔄 Filtro Anti-Appends: Seleccionada la última iteración ({len(df)} de {total_raw_packets} paquetes).")
        elif 'Creation_Cycle' in df.columns and (df['Creation_Cycle'].diff() < 0).any():
            drops = df['Creation_Cycle'].diff() < 0
            last_reset = drops[drops].index[-1]
            df = df.loc[last_reset:].copy()
            print(f"🔄 Filtro Anti-Appends (por ciclo): Seleccionada la última iteración ({len(df)} de {total_raw_packets} paquetes).")
    else:
        print(f"ℹ️ Modo todas las iteraciones activado: {len(df)} paquetes cargados.")

    df_sorted = df.sort_values(by='PID', ascending=True).reset_index(drop=True)
    n_total = len(df_sorted)

    # 2. GENERACIÓN DE PÁGINAS EN SUBDIRECTORIO gantt/
    gantt_dir = os.path.join(args.folder, "gantt")
    os.makedirs(gantt_dir, exist_ok=True)

    samples = args.samples
    total_pages = math.ceil(n_total / samples)
    pages_to_render = total_pages if args.max_pages <= 0 else min(total_pages, args.max_pages)

    print(f"📑 Generando {pages_to_render} páginas paginadas en: {gantt_dir}")

    for p in range(pages_to_render):
        start_row = p * samples
        end_row = min(n_total, (p + 1) * samples)
        df_page = df_sorted.iloc[start_row:end_row]
        
        min_p = int(df_page['PID'].min())
        max_p = int(df_page['PID'].max())
        
        page_num = p + 1
        page_filename = f"gantt_page_{page_num:03d}_pids_{min_p}_to_{max_p}.png"
        out_page_path = os.path.join(gantt_dir, page_filename)
        
        title = f"Gantt de Tráfico NoC - Página {page_num}/{total_pages} (PIDs {min_p} a {max_p})"
        render_gantt_page(df_page, title, out_page_path)

    # 3. GRÁFICOS RESUMEN EN LA RAÍZ DE LA CARPETA DE RESULTADOS
    print("\n📊 Generando visualizaciones resumen en la raíz del experimento...")
    
    # Gráfico 1: Fase libre
    df_libre = df_sorted.head(samples)
    render_gantt_page(df_libre,
                      f"1. Fase Libre (Flujo Ideal NoC) - Primeros {len(df_libre)} PIDs",
                      os.path.join(args.folder, "gantt_1_fase_libre.png"),
                      is_summary=True)

    # Gráfico 2: Congestión Media (> 1500 ciclos)
    df_media = get_pid_window(df_sorted, threshold=1500, samples=samples)
    if not df_media.empty:
        target_pid = int(df_media.iloc[len(df_media)//2]['PID'])
        render_gantt_page(df_media,
                          f"2. Inicio de Congestión en NoC (Entorno PID {target_pid})",
                          os.path.join(args.folder, "gantt_2_congestion_media.png"),
                          is_summary=True)
    else:
        print("ℹ️ No se detectaron paquetes con latencia > 1500 ciclos para gantt_2.")

    # Gráfico 3: Congestión Crítica (> 2000 ciclos)
    df_critica = get_pid_window(df_sorted, threshold=2000, samples=samples)
    if not df_critica.empty:
        target_pid = int(df_critica.iloc[len(df_critica)//2]['PID'])
        render_gantt_page(df_critica,
                          f"3. Cuello de Botella Masivo All-to-All (Entorno PID {target_pid})",
                          os.path.join(args.folder, "gantt_3_congestion_critica.png"),
                          is_summary=True)
    else:
        print("ℹ️ No se detectaron paquetes con latencia > 2000 ciclos para gantt_3.")

    print("\n🏁 Proceso de visualización completado exitosamente.")

if __name__ == "__main__":
    main()