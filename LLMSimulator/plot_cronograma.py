import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import glob

def parse_args():
    parser = argparse.ArgumentParser(description="Genera el Cronograma Cíclico de las GPUs")
    parser.add_argument("folder", type=str, help="Ruta a la carpeta de resultados")
    parser.add_argument("--window", type=int, default=100000, help="Tamaño de la ventana de tiempo en ns")
    return parser.parse_args()

def load_all_trcs(folder):
    all_data = []
    trc_files = glob.glob(os.path.join(folder, "*device_*.trc"))
    if not trc_files:
        print(f"❌ Error: No se encontraron archivos .trc en {folder}")
        return pd.DataFrame()

    for file in trc_files:
        basename = os.path.basename(file)
        gpu_id = int(basename.split('_')[-1].split('.')[0])
        df = pd.read_csv(file, on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        df['GPU'] = gpu_id
        df['START_NS'] = pd.to_numeric(df['START_NS'], errors='coerce')
        df['END_NS'] = pd.to_numeric(df['END_NS'], errors='coerce')
        df['DURATION'] = pd.to_numeric(df['DURATION'], errors='coerce')
        df['TYPE'] = df['TYPE'].str.strip()
        if 'DETAILS' in df.columns:
            df['DETAILS'] = df['DETAILS'].fillna("").astype(str).str.strip()
        else:
            df['DETAILS'] = ""
        
        # Eliminar filas corruptas
        df = df.dropna(subset=['START_NS', 'END_NS', 'DURATION'])
        
        # --- FILTRO ANTI-APPENDS ---
        # Detectamos si el tiempo retrocede (indicativo de que hay simulaciones concatenadas)
        drops = df['START_NS'].diff() < 0
        if drops.any():
            # Cortamos el DataFrame para quedarnos exclusivamente con la última simulación
            last_drop_idx = drops[drops].index[-1]
            df = df.loc[last_drop_idx:].copy()
            
        df = df[df['DURATION'] > 0]
        all_data.append(df)
        
    return pd.concat(all_data, ignore_index=True)

def classify_operation(op_type, details=""):
    """
    Clasifica el evento devolviendo (color, etiqueta_principal, subetiqueta_real).
    Para eventos de cómputo devuelve etiqueta 'Calc' y la operación real abajo (Linear, Attention, ExpertFFN...)
    """
    op = (str(op_type) + " " + str(details)).lower()
    
    # 1. Tránsito de Red
    if "scatter" in op:
        return "#1f77b4", "Scatter", None
    elif "gather" in op:
        return "#1f77b4", "Gather", None
    elif "all_reduce" in op:
        return "#17becf", "AllRed", None
        
    # 2. Bloqueos de Sincronización
    elif "stall" in op:
        return "#d62728", "Stall", None
        
    # 3. Operaciones de Cómputo (Verde #2ca02c)
    elif "expert" in op or "ffn" in op:
        return "#2ca02c", "Calc", "ExpertFFN"
    elif "attention" in op or "attn" in op:
        return "#2ca02c", "Calc", "Attention"
    elif "norm" in op:
        return "#2ca02c", "Calc", "LayerNorm"
    elif "residual" in op:
        return "#2ca02c", "Calc", "Residual"
    elif "rope" in op:
        return "#2ca02c", "Calc", "RoPE"
    elif "linear" in op:
        return "#2ca02c", "Calc", "Linear"
    elif "activation" in op or "act" in op:
        return "#2ca02c", "Calc", "Activation"
    else:
        # Fallback para operaciones de cálculo genéricas o históricas
        sub = "Linear" if "pop_operation" in op else str(op_type)[:10]
        return "#2ca02c", "Calc", sub

def load_packet_tracking(folder):
    """
    Carga packet_tracking_debug.csv de la misma carpeta, aísla la última iteración
    y extrae estadísticas por operación (Op_Type, Op_Idx).
    """
    csv_path = os.path.join(folder, "packet_tracking_debug.csv")
    if not os.path.exists(csv_path):
        return []
    
    try:
        df_p = pd.read_csv(csv_path)
        if df_p.empty or 'Op_Type' not in df_p.columns:
            return []
        
        # Filtro Anti-Appends: aislar la última iteración si hubo reinicios de reloj
        if 'Op_Start_NS' in df_p.columns:
            drops = df_p['Op_Start_NS'].diff() < 0
            if drops.any():
                last_drop_idx = drops[drops].index[-1]
                df_p = df_p.loc[last_drop_idx:].copy()
        
        ops = []
        for (op_type, op_idx), grp in df_p.groupby(['Op_Type', 'Op_Idx'], sort=False):
            start_ns = float(grp['Op_Start_NS'].iloc[0])
            end_ns = float(grp['Op_End_NS'].iloc[0])
            min_pid = int(grp['PID'].min())
            max_pid = int(grp['PID'].max())
            total_pkts = len(grp)
            final_avg_lat = float(grp['Avg_Flit_Latency'].iloc[-1])
            final_prod = float(grp['Throughput'].iloc[-1])
            ops.append({
                'type': str(op_type),
                'idx': int(op_idx),
                'start_ns': start_ns,
                'end_ns': end_ns,
                'min_pid': min_pid,
                'max_pid': max_pid,
                'total_pkts': total_pkts,
                'avg_flit_lat': final_avg_lat,
                'throughput': final_prod
            })
        return ops
    except Exception as e:
        print(f"⚠️ Aviso al cargar packet_tracking_debug.csv: {e}")
        return []

def match_network_op(label, start_ns, end_ns, ops):
    if not ops:
        return None
    for op in ops:
        if op['type'].lower() in label.lower() or label.lower() in op['type'].lower():
            if (start_ns < op['end_ns'] + 50.0 and end_ns > op['start_ns'] - 50.0):
                return op
    return None

def generate_window_plot(df, start_ns, end_ns, window_idx, output_dir, network_ops=None):
    mask = (df['START_NS'] < end_ns) & (df['END_NS'] > start_ns)
    df_window = df[mask].copy()
    if df_window.empty: return

    # Extraer clasificación y subetiquetas
    parsed = df_window.apply(lambda r: classify_operation(r['TYPE'], r['DETAILS']), axis=1)
    df_window['COLOR'] = [p[0] for p in parsed]
    df_window['LABEL'] = [p[1] for p in parsed]
    df_window['SUBLABEL'] = [p[2] for p in parsed]

    # Fusión Algorítmica de Eventos:
    # Coalescemos si pertenecen a la misma GPU y a la misma operación principal y subetiqueta
    df_window = df_window.sort_values(by=['GPU', 'START_NS']).reset_index(drop=True)
    df_window['group'] = ((df_window['SUBLABEL'] != df_window['SUBLABEL'].shift(1)) | 
                          (df_window['LABEL'] != df_window['LABEL'].shift(1)) | 
                          (df_window['GPU'] != df_window['GPU'].shift(1))).cumsum()
    
    df_merged = df_window.groupby(['GPU', 'COLOR', 'LABEL', 'SUBLABEL', 'group'], as_index=False, dropna=False).agg(
        START_NS=('START_NS', 'min'),
        END_NS=('END_NS', 'max')
    ).sort_values(by=['GPU', 'START_NS'])

    num_gpus = int(df['GPU'].max()) + 1
    fig, ax = plt.subplots(figsize=(16, 8))
    
    for i in range(num_gpus):
        ax.axhline(i, color='gray', linestyle=':', alpha=0.3)

    for _, row in df_merged.iterrows():
        gpu = row['GPU']
        dibujo_start = max(start_ns, row['START_NS'])
        dibujo_end = min(end_ns, row['END_NS'])
        dibujo_duration = dibujo_end - dibujo_start
        color = row['COLOR']
        label = row['LABEL']
        sublabel = row['SUBLABEL']
        
        # Alpha=1.0 para colores puros, sin borde intermedio
        rect = patches.Rectangle((dibujo_start, gpu - 0.4), dibujo_duration, 0.8, 
                                 linewidth=0.5, edgecolor='black', facecolor=color, alpha=1.0)
        ax.add_patch(rect)
        
        rel_w = dibujo_duration / (end_ns - start_ns)
        # Etiquetado cuando el bloque es suficientemente ancho (> 2.5% de la ventana)
        if rel_w > 0.025:
            x_center = dibujo_start + (dibujo_duration / 2)
            if label == "Calc" and sublabel:
                # Mostrar 'Calc' arriba y el nombre de la operación real justo abajo en NEGRITA
                ax.text(x_center, gpu + 0.12, "Calc", ha='center', va='center', 
                        color='white', fontsize=8.5)
                ax.text(x_center, gpu - 0.14, sublabel, ha='center', va='center', 
                        color='white', fontweight='bold', fontsize=8.5)
            elif label in ["Scatter", "Gather"]:
                net_op = match_network_op(label, row['START_NS'], row['END_NS'], network_ops)
                if net_op and rel_w > 0.08:
                    op_title = f"{net_op['type']} Nº{net_op['idx']}"
                    op_pids = f"PIDs {net_op['min_pid']}-{net_op['max_pid']} ({net_op['total_pkts']} pkts)"
                    op_metrics = f"Lat.Mitja: {net_op['avg_flit_lat']:.1f}c | Prod: {net_op['throughput']:.2f} flits/c"
                    ax.text(x_center, gpu + 0.22, op_title, ha='center', va='center', 
                            color='white', fontweight='bold', fontsize=8.0)
                    ax.text(x_center, gpu + 0.01, op_pids, ha='center', va='center', 
                            color='#e0f3ff', fontsize=7.2)
                    ax.text(x_center, gpu - 0.20, op_metrics, ha='center', va='center', 
                            color='#ffd180', fontsize=7.2)
                elif net_op and rel_w > 0.04:
                    op_line1 = f"{net_op['type']} Nº{net_op['idx']} ({net_op['total_pkts']} pkts)"
                    op_line2 = f"Lat: {net_op['avg_flit_lat']:.1f}c | Prod: {net_op['throughput']:.2f} f/c"
                    ax.text(x_center, gpu + 0.12, op_line1, ha='center', va='center', 
                            color='white', fontweight='bold', fontsize=7.5)
                    ax.text(x_center, gpu - 0.14, op_line2, ha='center', va='center', 
                            color='#ffd180', fontsize=7.0)
                elif net_op:
                    ax.text(x_center, gpu, f"{net_op['type']} Nº{net_op['idx']}", ha='center', va='center', 
                            color='white', fontweight='bold', fontsize=8.5)
                else:
                    ax.text(x_center, gpu, label, ha='center', va='center', 
                            color='white', fontweight='bold', fontsize=9)
            else:
                ax.text(x_center, gpu, label, ha='center', va='center', 
                        color='white', fontweight='bold', fontsize=9)

    ax.set_xlim(start_ns, end_ns)
    ax.set_ylim(-1, num_gpus)
    ax.set_yticks(range(num_gpus))
    ax.set_yticklabels([f'GPU {i}' for i in range(num_gpus)], fontweight='bold')
    ax.set_xlabel('Tiempo Global (Nanosegundos)', fontsize=12, fontweight='bold')
    ax.set_title(f'Cronograma de Ejecución Causal: {start_ns} ns a {end_ns} ns', fontsize=14, fontweight='bold')
    
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#2ca02c', lw=6, label='Cómputo (Calc: Linear, Attention, ExpertFFN...)'),
        Line2D([0], [0], color='#1f77b4', lw=6, label='Red (MoE Scatter/Gather con PIDs y Flit Metrics)'),
        Line2D([0], [0], color='#d62728', lw=6, label='Bloqueo (NETWORK_STALL)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9)

    plt.tight_layout()
    filename = f"timeline_part_{window_idx:03d}_{start_ns//1000}k_to_{end_ns//1000}k.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=150)
    plt.close(fig)

def main():
    args = parse_args()
    df = load_all_trcs(args.folder)
    if df.empty: return
    output_dir = os.path.join(args.folder, "cycle-to-cycle")
    os.makedirs(output_dir, exist_ok=True)
    
    network_ops = load_packet_tracking(args.folder)
    if network_ops:
        print(f"📊 Información de red vinculada: {len(network_ops)} operaciones de red encontradas en packet_tracking_debug.csv.")
    
    max_time = int(df['END_NS'].max())
    window_idx = 1
    for start_ns in range(0, max_time + 1, args.window):
        end_ns = start_ns + args.window
        generate_window_plot(df, start_ns, end_ns, window_idx, output_dir, network_ops)
        window_idx += 1
        
    print(f"✅ Cronogramas generados en: {output_dir}")

if __name__ == "__main__":
    main()