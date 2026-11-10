import os
import sys

# Asegurar configuración y caché de matplotlib en directorio con permisos de escritura
os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib_tfm')

# Fallback: Asegurar resolución de dependencias (pandas, matplotlib, numpy) en entornos contenidos
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_possible_site_packages = [
    os.path.join(os.path.dirname(__file__), ".venv", "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),
    os.path.join(_workspace_root, ".venv", "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),
    os.path.join(_workspace_root, ".venv", "lib64", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),
    os.path.expanduser(f"~/.local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
]
for _p in _possible_site_packages:
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import argparse
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="TFM Phase 5: Trace Analyzer (Macro Latency Breakdown & Network Saturation Curve)")
    parser.add_argument("--recent", type=int, default=3, help="Número de ejecuciones más recientes a analizar (por defecto: 3)")
    parser.add_argument("--model", type=str, default=None, help="Filtrar por modelo (ej. mixtral)")
    parser.add_argument("--today", action="store_true", help="Analizar solo las ejecuciones del día de hoy")
    parser.add_argument("--dir", type=str, default=None, help="Directorio base de los resultados (por defecto: busca build/results o LLMSimulator/build/results)")
    parser.add_argument("--unit", type=str, choices=["ns", "ms"], default="ns", help="Unidad temporal de visualización: ns o ms (por defecto: ns)")
    parser.add_argument("--semilog", action="store_true", default=False, help="Forzar escala semilogarítmica en el eje Y para la curva de saturación de red")
    return parser.parse_args()

def resolve_base_dir(custom_dir=None):
    """Resuelve la ruta correcta del directorio build/results."""
    if custom_dir and os.path.exists(custom_dir):
        return os.path.abspath(custom_dir)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "build", "results"),
        os.path.join(os.getcwd(), "build", "results"),
        os.path.join(os.getcwd(), "LLMSimulator", "build", "results"),
        "build/results",
        "LLMSimulator/build/results"
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath("build/results")

def get_target_folders(base_dir, args):
    """Busca, filtra y ordena cronológicamente las carpetas de resultados."""
    if not os.path.exists(base_dir):
        print(f"❌ Error: El directorio {base_dir} no existe.")
        return []

    folders = []
    today_str = datetime.now().strftime("%Y%m%d")

    for f in os.listdir(base_dir):
        path = os.path.join(base_dir, f)
        if os.path.isdir(path):
            parts = f.split('_')
            if len(parts) >= 5:
                model = parts[0]
                date_str = parts[-2]

                if args.model and model != args.model:
                    continue
                if args.today and date_str != today_str:
                    continue
                
                timestamp_str = parts[-2] + parts[-1]
                folders.append((timestamp_str, path, f))

    folders.sort(key=lambda x: x[0], reverse=True)
    return folders[:args.recent]

def analyze_folder(folder_path, folder_name):
    """
    Extrae métricas precisas del archivo .trc por GPU aplicando el filtro anti-appends.
    Calcula el tiempo real de Wall-Clock por inferencia individual y el promedio por dispositivo.
    """
    trc_files = glob.glob(os.path.join(folder_path, "*device_*.trc"))
    if not trc_files:
        return None

    compute_total = 0.0
    transit_total = 0.0
    stall_total = 0.0
    scatter_total = 0.0
    gather_total = 0.0
    devices_counted = 0
    min_cluster_start = float('inf')
    max_cluster_end = 0.0

    for filepath in sorted(trc_files):
        try:
            df = pd.read_csv(filepath, on_bad_lines='skip')
        except Exception:
            continue

        df.columns = df.columns.str.strip()
        df['START_NS'] = pd.to_numeric(df['START_NS'], errors='coerce')
        df['END_NS'] = pd.to_numeric(df['END_NS'], errors='coerce')
        df['DURATION'] = pd.to_numeric(df['DURATION'], errors='coerce')
        df = df.dropna(subset=['START_NS', 'END_NS', 'DURATION'])

        # --- FILTRO ANTI-APPENDS (Aislar última inferencia/iteración si iter > 1) ---
        drops = df['START_NS'].diff() < 0
        if drops.any():
            last_drop_idx = drops[drops].index[-1]
            df = df.loc[last_drop_idx:].copy()

        df = df[df['DURATION'] > 0]
        if df.empty:
            continue

        dev_start = df['START_NS'].min()
        dev_end = df['END_NS'].max()
        min_cluster_start = min(min_cluster_start, dev_start)
        max_cluster_end = max(max_cluster_end, dev_end)

        df['TYPE'] = df['TYPE'].astype(str).str.strip()

        # 1. Network Transit (Tiempo de vuelo de paquetes flit en BookSim2)
        scatter = df[df['TYPE'].str.contains('scatter', case=False, na=False)]['DURATION'].sum()
        gather = df[df['TYPE'].str.contains('gather', case=False, na=False)]['DURATION'].sum()
        all_reduce = df[df['TYPE'].str.contains('all_reduce', case=False, na=False)]['DURATION'].sum()
        transit = scatter + gather + all_reduce

        # 2. Synchronization Stalls (Espera activa en barreras de sincronización BSP)
        stall = df[df['TYPE'].str.contains('stall', case=False, na=False)]['DURATION'].sum()

        # 3. Compute Time (Operaciones matemáticas en la GPU)
        non_compute_mask = df['TYPE'].str.contains('scatter|gather|stall|all_reduce', case=False, na=False)
        compute = df[~non_compute_mask]['DURATION'].sum()

        compute_total += compute
        transit_total += transit
        stall_total += stall
        scatter_total += scatter
        gather_total += gather
        devices_counted += 1

    if devices_counted == 0:
        return None

    cluster_wall_clock = max_cluster_end - min_cluster_start
    c_avg = compute_total / devices_counted
    t_avg = transit_total / devices_counted
    s_avg = stall_total / devices_counted
    scat_avg = scatter_total / devices_counted
    gath_avg = gather_total / devices_counted
    tot_avg = c_avg + t_avg + s_avg

    return {
        'Configuración': folder_name,
        'Num GPUs': devices_counted,
        'Compute Time (ns)': c_avg,
        'Network Transit Time (ns)': t_avg,
        'Network Stalls (ns)': s_avg,
        'Total Mean Latency (ns)': tot_avg,
        'Wall-Clock Time (ns)': cluster_wall_clock,
        'MoE Scatter (ns)': scat_avg,
        'MoE Gather (ns)': gath_avg,
        'Discrepancy (ns)': cluster_wall_clock - tot_avg
    }

def extract_network_stats(folder_path, folder_name, num_gpus):
    """
    Parsea packet_tracking_debug.csv aplicando el filtro anti-appends.
    Calcula:
      - Tasa de inyección media lambda (flits/ciclo/nodo y paquetes/ciclo/nodo).
      - Latencia media de red (Avg_Flit_Latency y Total_Latency en ciclos de BookSim2).
      - Metadatos arquitecturales (Topología, VCs, Batch Size).
    """
    csv_path = os.path.join(folder_path, "packet_tracking_debug.csv")
    if not os.path.exists(csv_path):
        print(f"⚠️ Aviso: No se encontró 'packet_tracking_debug.csv' en {folder_name}. Se omitirá de la curva de saturación.")
        return None

    try:
        df = pd.read_csv(csv_path, on_bad_lines='skip')
    except Exception as e:
        print(f"⚠️ Aviso: Error leyendo {csv_path} ({e}). Se omitirá de la curva de saturación.")
        return None

    if df.empty:
        print(f"⚠️ Aviso: 'packet_tracking_debug.csv' en {folder_name} está vacío. Se omitirá de la curva de saturación.")
        return None

    # Normalización de columnas y compatibilidad con formatos antiguos
    df.columns = df.columns.str.strip()
    if 'Total_Latency' not in df.columns and 'Latency' in df.columns:
        df['Total_Latency'] = df['Latency']
    if 'Network_Latency' not in df.columns and 'Total_Latency' in df.columns:
        df['Network_Latency'] = df['Total_Latency']
    if 'Avg_Flit_Latency' not in df.columns:
        df['Avg_Flit_Latency'] = df['Total_Latency']
    if 'Num_Flits' not in df.columns:
        df['Num_Flits'] = 9
    if 'Size_Bytes' not in df.columns:
        df['Size_Bytes'] = 288
    if 'Creation_Cycle' not in df.columns and 'Inject_Cycle' in df.columns:
        df['Creation_Cycle'] = df['Inject_Cycle']
    if 'Receive_Cycle' not in df.columns and 'Creation_Cycle' in df.columns and 'Total_Latency' in df.columns:
        df['Receive_Cycle'] = df['Creation_Cycle'] + df['Total_Latency']

    for col in ['Creation_Cycle', 'Inject_Cycle', 'Receive_Cycle', 'Total_Latency', 'Avg_Flit_Latency', 'Num_Flits', 'Op_Start_NS']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Filtro Anti-Appends para aislar la última iteración
    if 'Op_Start_NS' in df.columns and not df['Op_Start_NS'].isna().all():
        drops = df['Op_Start_NS'].diff() < 0
        if drops.any():
            last_reset = drops[drops].index[-1]
            df = df.loc[last_reset:].copy()
    elif 'Creation_Cycle' in df.columns:
        drops = df['Creation_Cycle'].diff() < -1000
        if drops.any():
            last_reset = drops[drops].index[-1]
            df = df.loc[last_reset:].copy()

    df = df.dropna(subset=['Creation_Cycle', 'Receive_Cycle'])
    if df.empty:
        return None

    # Extracción de metadatos (Topología, VCs, BS)
    topology = "desconocida"
    num_vcs = "N/A"
    bs = "N/A"

    cfg_path = os.path.join(folder_path, "test.cfg")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r') as fp:
                for line in fp:
                    line = line.strip()
                    if line.startswith("topology"):
                        topology = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("num_vcs"):
                        num_vcs = line.split("=")[1].replace(";", "").strip()
        except Exception:
            pass

    # Batch size, Tensor Parallelism y Skewness desde config.yaml o nombre de carpeta
    config_yaml = os.path.join(folder_path, "config.yaml")
    tp = 1
    skewness = 0.0
    if os.path.exists(config_yaml):
        try:
            with open(config_yaml, 'r') as fp:
                for line in fp:
                    if "max_batch_size:" in line:
                        bs = line.split(":")[1].strip()
                    elif "none_expert_tensor_degree:" in line:
                        tp_str = line.split(":")[1].strip()
                        if tp_str.isdigit():
                            tp = int(tp_str)
                    elif "skewness:" in line:
                        skew_str = line.split(":")[1].strip()
                        try:
                            skewness = float(skew_str)
                        except Exception:
                            pass
        except Exception:
            pass

    if bs == "N/A" or topology == "desconocida" or tp == 1 or skewness == 0.0:
        for part in folder_name.split("_"):
            if part.startswith("bs") and bs == "N/A":
                bs = part[2:]
            elif part.startswith("tp") and tp == 1:
                val = part[2:]
                if val.isdigit():
                    tp = int(val)
            elif part.startswith("skew") and skewness == 0.0:
                val = part[4:]
                try:
                    skewness = float(val)
                except Exception:
                    pass
            elif part in ["torus", "mesh"] and topology == "desconocida":
                topology = part

    tp_tag = f", TP={tp}" if tp > 1 else ""
    skew_tag = f", Skew={skewness}" if skewness > 0.0 else ""
    label = f"{num_gpus}dev {topology.capitalize()} (VCs={num_vcs}, BS={bs}{tp_tag}{skew_tag})"

    # Cálculo de tasa de inyección lambda y latencias por colectiva
    op_points = []
    if 'Op_Type' in df.columns and 'Op_Idx' in df.columns:
        for (op_t, op_i), grp in df.groupby(['Op_Type', 'Op_Idx']):
            f_cnt = grp['Num_Flits'].sum()
            p_cnt = len(grp)
            dur = max(1.0, float(grp['Receive_Cycle'].max() - grp['Creation_Cycle'].min()))
            l_flits = f_cnt / (num_gpus * dur)
            l_pkts = p_cnt / (num_gpus * dur)
            lat_flits = float(grp['Avg_Flit_Latency'].mean())
            lat_pkts = float(grp['Total_Latency'].mean())
            op_points.append({
                'lambda_flits': l_flits,
                'lambda_pkts': l_pkts,
                'lat_flits': lat_flits,
                'lat_pkts': lat_pkts,
                'op_type': str(op_t),
                'op_idx': int(op_i) if str(op_i).isdigit() else op_i
            })
    else:
        f_cnt = df['Num_Flits'].sum()
        p_cnt = len(df)
        dur = max(1.0, float(df['Receive_Cycle'].max() - df['Creation_Cycle'].min()))
        l_flits = f_cnt / (num_gpus * dur)
        l_pkts = p_cnt / (num_gpus * dur)
        op_points.append({
            'lambda_flits': l_flits,
            'lambda_pkts': l_pkts,
            'lat_flits': float(df['Avg_Flit_Latency'].mean()),
            'lat_pkts': float(df['Total_Latency'].mean()),
            'op_type': 'Colectiva',
            'op_idx': 1
        })

    mean_lambda_flits = float(np.mean([p['lambda_flits'] for p in op_points]))
    mean_lambda_pkts = float(np.mean([p['lambda_pkts'] for p in op_points]))
    global_flit_lat = float(df['Avg_Flit_Latency'].mean())
    global_pkt_lat = float(df['Total_Latency'].mean())

    return {
        'Configuración': folder_name,
        'Etiqueta': label,
        'Topología': topology,
        'VCs': num_vcs,
        'BS': bs,
        'Num GPUs': num_gpus,
        'Lambda Flits (flits/cyc/nodo)': mean_lambda_flits,
        'Lambda Pkts (pkts/cyc/nodo)': mean_lambda_pkts,
        'Avg Flit Latency (ciclos)': global_flit_lat,
        'Avg Pkt Latency (ciclos)': global_pkt_lat,
        'Op Points': op_points,
        'Num Paquetes': len(df)
    }

def main():
    args = parse_args()
    base_dir = resolve_base_dir(args.dir)
    target_folders = get_target_folders(base_dir, args)

    if not target_folders:
        print(f"⚠️ No se encontraron resultados que coincidan con los filtros en {base_dir}")
        return

    print(f"📊 Fase 5: Analizando las {len(target_folders)} ejecuciones seleccionadas desde:")
    print(f"📁 Directorio base: {base_dir}\n")

    # Invertir para orden cronológico ascendente en las gráficas
    target_folders.reverse()

    results = []
    net_results = []

    for _, folder_path, folder_name in target_folders:
        short_label = "_".join(folder_name.split('_')[:-2])
        stats = analyze_folder(folder_path, short_label)
        if stats:
            results.append(stats)
            # Extraer métricas de red para la curva de saturación
            net_stats = extract_network_stats(folder_path, folder_name, stats['Num GPUs'])
            if net_stats:
                net_results.append(net_stats)

    if not results:
        print("❌ No se encontraron archivos .trc válidos en las carpetas seleccionadas.")
        return

    df = pd.DataFrame(results)

    # Imprimir tabla comparativa macroscópica de latencias en consola
    print("=" * 115)
    print(f"{'Configuración':<32} {'GPUs':<5} {'Compute (ns)':<15} {'Transit (ns)':<14} {'Stalls (ns)':<13} {'Total (ns)':<15} {'Wall-Clock (ns)':<16}")
    print("=" * 115)
    for _, row in df.iterrows():
        print(f"{row['Configuración']:<32} {row['Num GPUs']:<5} {row['Compute Time (ns)']:>14.1f} {row['Network Transit Time (ns)']:>13.1f} {row['Network Stalls (ns)']:>12.1f} {row['Total Mean Latency (ns)']:>14.1f} {row['Wall-Clock Time (ns)']:>15.1f}")
    print("=" * 115)

    # Imprimir tabla de saturación de red si hay trazas disponibles
    if net_results:
        print("\n" + "=" * 122)
        print("                        MÉTRICAS DE SATURACIÓN DE RED (BOOKSIM2 - PACKET TRACKING)")
        print("=" * 122)
        print(f"{'Configuración / Etiqueta':<38} {'Topología':<10} {'VCs':<5} {'BS':<5} {'GPUs':<5} {'λ (flits/c/nodo)':<18} {'Lat. Flit (c)':<15} {'Lat. Pkt (c)':<15}")
        print("-" * 122)
        for nr in net_results:
            print(f"{nr['Etiqueta']:<38} {nr['Topología']:<10} {str(nr['VCs']):<5} {str(nr['BS']):<5} {nr['Num GPUs']:<5} {nr['Lambda Flits (flits/cyc/nodo)']:>16.4f} {nr['Avg Flit Latency (ciclos)']:>14.1f} {nr['Avg Pkt Latency (ciclos)']:>14.1f}")
        print("=" * 122)

    df_plot = df.copy()
    df_plot.set_index('Configuración', inplace=True)

    # Crear la subcarpeta de análisis
    timestamp_analisis = datetime.now().strftime("%Y%m%d_%H%M%S")
    parent_build = os.path.dirname(base_dir)
    output_dir = os.path.join(parent_build, "analysis", f"analisis_{timestamp_analisis}")
    os.makedirs(output_dir, exist_ok=True)

    # Factores de conversión según la unidad seleccionada
    scale = 1.0 if args.unit == "ns" else 1e-6
    unit_label = "nanosegundos (ns)" if args.unit == "ns" else "milisegundos (ms)"

    # --- GRÁFICA 1: La Anatomía de la Latencia ---
    fig, ax = plt.subplots(figsize=(12, 7))
    plot_data = df_plot[['Compute Time (ns)', 'Network Transit Time (ns)', 'Network Stalls (ns)']] * scale

    bars = plot_data.plot(
        kind='bar', stacked=True, color=['#2ca02c', '#1f77b4', '#d62728'], ax=ax, width=0.55
    )
    plt.title('TFM: Anatomía de Latencia por Dispositivo (Cómputo vs Red vs Stalls)', fontsize=14, fontweight='bold', pad=15)
    plt.ylabel(f'Tiempo Real de Ejecución ({unit_label})', fontsize=12)
    plt.xlabel('Configuración de Red / Topología / Lote', fontsize=12)
    plt.xticks(rotation=15, ha='right', fontsize=10)
    plt.legend(["Compute Time (Procesamiento GPU)", "Network Transit (Viaje por BookSim2)", "Network Stalls (Espera de Sincronización)"], fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    for idx, (conf, row) in enumerate(df_plot.iterrows()):
        total_val = row['Total Mean Latency (ns)'] * scale
        text = f"{total_val:,.1f} ns\n({total_val/1e6:.3f} ms)" if args.unit == "ns" else f"{total_val:.3f} ms"
        ax.annotate(text,
                    xy=(idx, total_val),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85))

    y_max = plot_data.sum(axis=1).max() * 1.22
    ax.set_ylim(0, y_max)
    plt.tight_layout()

    plot1_path = os.path.join(output_dir, "anatomia_latencia.png")
    plt.savefig(plot1_path, dpi=300)
    plt.close()

    # --- GRÁFICA 2: Desglose MoE ---
    fig2, ax2 = plt.subplots(figsize=(12, 7))
    moe_data = df_plot[['MoE Scatter (ns)', 'MoE Gather (ns)']] * scale
    moe_data.plot(
        kind='bar', color=['#1f77b4', '#ff7f0e'], ax=ax2, width=0.55
    )
    plt.title('TFM: Coste de las Primitivas de Red MoE (Scatter vs Gather)', fontsize=14, fontweight='bold', pad=15)
    plt.ylabel(f'Tiempo Medio por GPU ({unit_label})', fontsize=12)
    plt.xlabel('Configuración de Red / Topología / Lote', fontsize=12)
    plt.xticks(rotation=15, ha='right', fontsize=10)
    plt.legend(["MoE Scatter (Distribución a Expertos)", "MoE Gather (Recolección de Resultados)"], fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    y_max_moe = moe_data.max().max() * 1.2
    ax2.set_ylim(0, y_max_moe)
    plt.tight_layout()

    plot2_path = os.path.join(output_dir, "desglose_primitivas_moe.png")
    plt.savefig(plot2_path, dpi=300)
    plt.close()

    # --- GRÁFICA 3: Curva de Saturación de Red (Latencia vs. Carga Inyectada) ---
    plot3_path = None
    if net_results:
        fig3, ax3 = plt.subplots(figsize=(13, 8))
        palette = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd', '#ff7f0e', '#17becf', '#e377c2', '#8c564b']
        marker_styles = ['o', 's', '^', 'D', 'v', 'p', '*', 'h']

        # Evaluar dispersión de latencias para determinar escala semilogarítmica
        all_lats = [pt['lat_flits'] for item in net_results for pt in item['Op Points']]
        lat_min = min(all_lats) if all_lats else min(item['Avg Flit Latency (ciclos)'] for item in net_results)
        lat_max = max(all_lats) if all_lats else max(item['Avg Flit Latency (ciclos)'] for item in net_results)
        use_semilog = args.semilog or ((lat_max / max(1.0, lat_min) >= 4.0) and (lat_max - lat_min > 500))

        # Ordenar por tasa de inyección para trazar la tendencia de saturación
        sorted_by_lambda = sorted(net_results, key=lambda x: x['Lambda Flits (flits/cyc/nodo)'])

        for idx, item in enumerate(net_results):
            col = palette[idx % len(palette)]
            mk = marker_styles[idx % len(marker_styles)]
            label_tag = item['Etiqueta']
            l_mean = item['Lambda Flits (flits/cyc/nodo)']
            lat_mean = item['Avg Flit Latency (ciclos)']

            # Nube de puntos de operaciones individuales (Scatter / Gather en cada capa)
            if item['Op Points']:
                xs_ops = [p['lambda_flits'] for p in item['Op Points']]
                ys_ops = [p['lat_flits'] for p in item['Op Points']]
                ax3.scatter(xs_ops, ys_ops, color=col, alpha=0.22, s=36, edgecolors='none', zorder=2)

            # Punto macroscópico representativo de la simulación
            ax3.scatter(l_mean, lat_mean, color=col, marker=mk, s=230,
                        edgecolors='black', linewidths=1.8, zorder=5,
                        label=f"{label_tag} (λ={l_mean:.4f}, Lat={lat_mean:.1f}c)")

            # Anotación destacada tipo badge
            ax3.annotate(
                f"{label_tag}\nλ={l_mean:.4f} flits/c/nodo\nLat={lat_mean:.1f} ciclos",
                xy=(l_mean, lat_mean),
                xytext=(15, 12), textcoords="offset points",
                fontsize=8.5, fontweight='semibold',
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=col, alpha=0.92, lw=1.2),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.15", color=col, lw=1.2),
                zorder=6
            )

        # Línea discontinua de tendencia de red
        if len(sorted_by_lambda) >= 2:
            xs_trend = [item['Lambda Flits (flits/cyc/nodo)'] for item in sorted_by_lambda]
            ys_trend = [item['Avg Flit Latency (ciclos)'] for item in sorted_by_lambda]
            ax3.plot(xs_trend, ys_trend, linestyle='--', color='#555555', alpha=0.55, linewidth=1.5, zorder=3, label='Tendencia de Saturación')

        if use_semilog:
            ax3.set_yscale('log')
            ax3.set_ylabel('Latencia Media de Red [ciclos BookSim2] (Escala Logarítmica)', fontsize=12, fontweight='semibold')
        else:
            ax3.set_ylabel('Latencia Media de Red [ciclos BookSim2]', fontsize=12, fontweight='semibold')
            ax3.set_ylim(bottom=0)

        ax3.set_xlabel(r'Tasa Media de Inyección Real $\lambda$ [flits / ciclo / nodo]', fontsize=12, fontweight='semibold')
        ax3.set_title('TFM: Curva de Saturación de Red NoC (Latencia vs. Carga Inyectada)', fontsize=14, fontweight='bold', pad=15)
        ax3.grid(True, which='both', linestyle=':', alpha=0.55, color='#888888', zorder=1)
        ax3.legend(fontsize=9.5, loc='upper left', framealpha=0.92, edgecolor='#cccccc')

        plt.tight_layout()
        plot3_path = os.path.join(output_dir, "curva_saturacion_red.png")
        plt.savefig(plot3_path, dpi=300)
        plt.close()
    else:
        print("ℹ️ No se encontraron trazas 'packet_tracking_debug.csv' válidas. Se omite la generación de 'curva_saturacion_red.png'.")

    print(f"\n✅ Análisis completado con éxito.")
    print(f"📦 Gráficas generadas y guardadas en: {output_dir}")
    print(f"   - {plot1_path}")
    print(f"   - {plot2_path}")
    if plot3_path:
        print(f"   - {plot3_path}")

if __name__ == "__main__":
    main()
