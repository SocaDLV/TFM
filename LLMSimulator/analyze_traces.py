import os
import argparse
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="TFM Phase 5: Trace Analyzer (Macro Latency Breakdown)")
    parser.add_argument("--recent", type=int, default=3, help="Número de ejecuciones más recientes a analizar (por defecto: 3)")
    parser.add_argument("--model", type=str, default=None, help="Filtrar por modelo (ej. mixtral)")
    parser.add_argument("--today", action="store_true", help="Analizar solo las ejecuciones del día de hoy")
    parser.add_argument("--dir", type=str, default=None, help="Directorio base de los resultados (por defecto: busca build/results o LLMSimulator/build/results)")
    parser.add_argument("--unit", type=str, choices=["ns", "ms"], default="ns", help="Unidad temporal de visualización: ns o ms (por defecto: ns)")
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

def main():
    args = parse_args()
    base_dir = resolve_base_dir(args.dir)
    target_folders = get_target_folders(base_dir, args)

    if not target_folders:
        print(f"⚠️ No se encontraron resultados que coincidan con los filtros en {base_dir}")
        return

    print(f"📊 Fase 5: Analizando las {len(target_folders)} ejecuciones seleccionadas desde:")
    print(f"📁 Directorio base: {base_dir}\n")
    
    results = []
    for _, folder_path, folder_name in target_folders:
        short_label = "_".join(folder_name.split('_')[:-2])
        stats = analyze_folder(folder_path, short_label)
        if stats:
            results.append(stats)

    if not results:
        print("❌ No se encontraron archivos .trc válidos en las carpetas seleccionadas.")
        return

    # Invertir para orden cronológico ascendente en las gráficas
    results.reverse()
    df = pd.DataFrame(results)

    # Imprimir tabla comparativa en consola
    print("=" * 115)
    print(f"{'Configuración':<32} {'GPUs':<5} {'Compute (ns)':<15} {'Transit (ns)':<14} {'Stalls (ns)':<13} {'Total (ns)':<15} {'Wall-Clock (ns)':<16}")
    print("=" * 115)
    for _, row in df.iterrows():
        print(f"{row['Configuración']:<32} {row['Num GPUs']:<5} {row['Compute Time (ns)']:>14.1f} {row['Network Transit Time (ns)']:>13.1f} {row['Network Stalls (ns)']:>12.1f} {row['Total Mean Latency (ns)']:>14.1f} {row['Wall-Clock Time (ns)']:>15.1f}")
    print("=" * 115)

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
    fmt = "{:,.0f} ns" if args.unit == "ns" else "{:.3f} ms"
    
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

    # Añadir etiquetas con el total encima de cada barra
    for idx, (conf, row) in enumerate(df_plot.iterrows()):
        total_val = row['Total Mean Latency (ns)'] * scale
        wall_val = row['Wall-Clock Time (ns)'] * scale
        text = f"{total_val:,.1f} ns\n({total_val/1e6:.3f} ms)" if args.unit == "ns" else f"{total_val:.3f} ms"
        ax.annotate(text,
                    xy=(idx, total_val),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85))

    # Margen superior para que quepan las etiquetas
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

    # Margen superior
    y_max_moe = moe_data.max().max() * 1.2
    ax2.set_ylim(0, y_max_moe)
    plt.tight_layout()
    
    plot2_path = os.path.join(output_dir, "desglose_primitivas_moe.png")
    plt.savefig(plot2_path, dpi=300)
    plt.close()

    print(f"\n✅ Análisis completado con éxito.")
    print(f"📦 Gráficas generadas y guardadas en: {output_dir}")
    print(f"   - {plot1_path}")
    print(f"   - {plot2_path}")

if __name__ == "__main__":
    main()