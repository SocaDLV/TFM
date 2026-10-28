import os
import argparse
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D

def parse_args():
    parser = argparse.ArgumentParser(description="Genera el Cronograma Cíclico de las GPUs con enriquecimiento micro-arquitectural")
    parser.add_argument("folder", type=str, help="Ruta a la carpeta de resultados")
    parser.add_argument("--window", type=int, default=100000, help="Tamaño de la ventana de tiempo en ns")
    return parser.parse_args()

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

def parse_trc_file(file):
    """
    Parsea un archivo .trc individual de GPU, filtra appends, infiere capas del LLM,
    clasifica macro y micro-operaciones, y coalesce eventos en macro-bloques homogéneos.
    """
    basename = os.path.basename(file)
    gpu_id = int(basename.split('_')[-1].split('.')[0])
    df = pd.read_csv(file, on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['GPU'] = gpu_id
    df['START_NS'] = pd.to_numeric(df['START_NS'], errors='coerce')
    df['END_NS'] = pd.to_numeric(df['END_NS'], errors='coerce')
    df['DURATION'] = pd.to_numeric(df['DURATION'], errors='coerce')
    df['TYPE'] = df['TYPE'].astype(str).str.strip()
    df['DETAILS'] = df['DETAILS'].fillna("").astype(str).str.strip()
    df = df.dropna(subset=['START_NS', 'END_NS', 'DURATION'])
    
    # Filtro Anti-Appends (aislar la última iteración)
    drops = df['START_NS'].diff() < 0
    if drops.any():
        last_drop_idx = drops[drops].index[-1]
        df = df.loc[last_drop_idx:].copy()
    df = df[df['DURATION'] > 0].reset_index(drop=True)
    if df.empty:
        return []

    # 1. Extracción de Capa del LLM (MoE_decoder_X o decoder_X)
    explicit_layer = df['DETAILS'].str.extract(r'(?:MoE_decoder_|decoder_)(\d+)')[0]
    df['EXPLICIT_LAYER'] = pd.to_numeric(explicit_layer, errors='coerce')
    layers = [None] * len(df)
    for i in range(len(df)):
        if pd.notna(df.at[i, 'EXPLICIT_LAYER']):
            layers[i] = int(df.at[i, 'EXPLICIT_LAYER'])
        elif 'input_layer_norm' in df.at[i, 'TYPE'].lower():
            for j in range(i + 1, min(i + 5, len(df))):
                if pd.notna(df.at[j, 'EXPLICIT_LAYER']):
                    layers[i] = int(df.at[j, 'EXPLICIT_LAYER'])
                    break
    df['LAYER'] = pd.Series(layers).ffill().bfill().fillna(0).astype(int)

    # 2. Extracción de Métricas de Cuello de Botella (Comp_ns y Mem_ns)
    comp_ns = df['DETAILS'].str.extract(r'Comp_ns:([0-9.]+)')[0]
    mem_ns = df['DETAILS'].str.extract(r'Mem_ns:([0-9.]+)')[0]
    df['COMP_NS'] = pd.to_numeric(comp_ns, errors='coerce').fillna(0.0)
    df['MEM_NS'] = pd.to_numeric(mem_ns, errors='coerce').fillna(0.0)

    # 3. Clasificación de Macro-Operación y Micro-Operación
    def classify(row):
        t = row['TYPE'].lower()
        d = row['DETAILS'].lower()
        op = t + " " + d

        if "scatter" in op:
            return "#1f77b4", "Scatter", "Scatter", "Scatter", None
        elif "gather" in op:
            return "#1f77b4", "Gather", "Gather", "Gather", None
        elif "all_reduce" in op:
            return "#17becf", "AllRed", "AllRed", "AllRed", None
        elif "stall" in op:
            return "#d62728", "Stall", "Stall", "Stall", None

        # Expert FFN
        exp_m = re.search(r'expert_ffn_(\d+)', op)
        if "expert_ffn" in op or exp_m:
            exp_id = int(exp_m.group(1)) if exp_m else None
            if "gate_proj" in op:
                micro = "Gate_Proj"
            elif "activation" in op or "act" in op:
                micro = "SiLU"
            elif "up_proj" in op:
                micro = "Up_Proj"
            elif "down_proj" in op:
                micro = "Down_Proj"
            else:
                micro = "FFN"
            return "#2ca02c", "Calc", "ExpertFFN", micro, exp_id

        # Attention block (Pre-LN, QKV, AttnGen, O_Proj, Res, Post-LN, Gate)
        if "attn_qkv" in op:
            return "#2ca02c", "Calc", "Attention", "QKV_Proj", None
        elif "attentiongen" in op or "self_attention" in op:
            return "#2ca02c", "Calc", "Attention", "AttnGen", None
        elif "attn_o_proj" in op:
            return "#2ca02c", "Calc", "Attention", "O_Proj", None
        elif "input_layer_norm" in op:
            return "#2ca02c", "Calc", "Attention", "LN", None
        elif "post_attn_layer_norm" in op:
            return "#2ca02c", "Calc", "Attention", "LN", None
        elif "residual_1" in op:
            return "#2ca02c", "Calc", "Attention", "Res", None
        elif "gate_fn" in op:
            return "#2ca02c", "Calc", "Attention", "Gate", None
        elif "residual_2" in op:
            return "#2ca02c", "Calc", "Residual", "Res", None
        else:
            sub = "Linear" if "pop_operation" in op else row['TYPE'][:10]
            return "#2ca02c", "Calc", sub, sub, None

    parsed = df.apply(classify, axis=1)
    df['COLOR'] = [p[0] for p in parsed]
    df['LABEL'] = [p[1] for p in parsed]
    df['MACRO_OP'] = [p[2] for p in parsed]
    df['MICRO_OP'] = [p[3] for p in parsed]
    df['EXP_ID'] = [p[4] for p in parsed]

    # 4. Agrupación y Coalescencia Causal Estricta por Capa y Macro-Operación
    df['group'] = ((df['LAYER'] != df['LAYER'].shift(1)) |
                   (df['LABEL'] != df['LABEL'].shift(1)) |
                   (df['MACRO_OP'] != df['MACRO_OP'].shift(1))).cumsum()

    blocks = []
    for _, grp in df.groupby('group', sort=False):
        first_row = grp.iloc[0]
        start_ns = grp['START_NS'].min()
        end_ns = grp['END_NS'].max()
        dur_ns = end_ns - start_ns
        macro_op = first_row['MACRO_OP']
        label = first_row['LABEL']
        layer = first_row['LAYER']
        color = first_row['COLOR']

        # Fronteras internas para líneas verticales discontinuas
        sub_divisions = [r['END_NS'] for _, r in grp.iloc[:-1].iterrows() if r['DURATION'] > 0.5]

        # Secuencia textual de operaciones
        if macro_op == "Attention":
            seq_str = "(LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)"
        elif macro_op == "ExpertFFN":
            exp_ids = sorted(list(set(int(e) for e in grp['EXP_ID'].dropna().unique())))
            if len(exp_ids) == 1:
                seq_str = f"(Exp#{exp_ids[0]}: Gate_Proj + SiLU + Up_Proj + Down_Proj)"
            elif len(exp_ids) > 1:
                ids_str = ",".join(str(e) for e in exp_ids)
                seq_str = f"(Exp#{ids_str}: {len(exp_ids)}x[Gate+SiLU+Up+Down])"
            else:
                seq_str = "(ExpertFFN: Gate + SiLU + Up + Down)"
        else:
            unique_micros = []
            for u in grp['MICRO_OP'].unique():
                if u not in unique_micros:
                    unique_micros.append(u)
            seq_str = f"({ ' + '.join(unique_micros) })"

        # Métricas de duración y cuello de botella
        dur_str = f"{dur_ns/1000.0:.1f}us" if dur_ns >= 1000.0 else f"{dur_ns:.0f}ns"
        tot_comp = grp['COMP_NS'].sum()
        tot_mem = grp['MEM_NS'].sum()
        if (tot_comp + tot_mem) > 0.0:
            mem_pct = (tot_mem / (tot_comp + tot_mem)) * 100.0
            bn_str = f"Mem-Bound {mem_pct:.1f}%" if mem_pct >= 50.0 else f"Compute-Bound {100.0 - mem_pct:.1f}%"
            line3 = f"Dur: {dur_str} ({bn_str})"
        else:
            line3 = f"Dur: {dur_str}"

        blocks.append({
            'GPU': gpu_id,
            'LAYER': layer,
            'LABEL': label,
            'MACRO_OP': macro_op,
            'COLOR': color,
            'START_NS': start_ns,
            'END_NS': end_ns,
            'DURATION': dur_ns,
            'SUB_DIVISIONS': sub_divisions,
            'SEQ_STR': seq_str,
            'LINE3': line3
        })

    return blocks

def generate_window_plot(all_blocks, start_ns, end_ns, window_idx, output_dir, network_ops=None):
    # Filtrar macro-bloques que se solapan con la ventana temporal actual
    blocks_window = [b for b in all_blocks if b['START_NS'] < end_ns and b['END_NS'] > start_ns]
    if not blocks_window:
        return

    num_gpus = max(b['GPU'] for b in all_blocks) + 1
    fig, ax = plt.subplots(figsize=(16, 8))
    
    for i in range(num_gpus):
        ax.axhline(i, color='gray', linestyle=':', alpha=0.3)

    for b in blocks_window:
        gpu = b['GPU']
        layer = b['LAYER']
        color = b['COLOR']
        label = b['LABEL']
        macro_op = b['MACRO_OP']
        dibujo_start = max(start_ns, b['START_NS'])
        dibujo_end = min(end_ns, b['END_NS'])
        dibujo_dur = dibujo_end - dibujo_start
        rel_w = dibujo_dur / (end_ns - start_ns)

        # 1. Dibujar rectángulo principal
        rect = patches.Rectangle((dibujo_start, gpu - 0.4), dibujo_dur, 0.8, 
                                 linewidth=0.5, edgecolor='black', facecolor=color, alpha=1.0)
        ax.add_patch(rect)

        # 2. Dibujar líneas verticales discontinuas internas para sub-operaciones principales
        for div_x in b['SUB_DIVISIONS']:
            if start_ns < div_x < end_ns:
                ax.vlines(x=div_x, ymin=gpu - 0.38, ymax=gpu + 0.38, 
                          color='white', linestyle='--', linewidth=0.75, alpha=0.6)

        # 3. Renderizado de texto adaptativo multilínea
        if rel_w > 0.025:
            x_center = dibujo_start + (dibujo_dur / 2.0)
            if label == 'Calc':
                if dibujo_dur >= 2500 and rel_w > 0.12:
                    ax.text(x_center, gpu + 0.22, f'Layer {layer} | Calc: {macro_op}', 
                            ha='center', va='center', color='white', fontsize=8.2)
                    ax.text(x_center, gpu + 0.01, b['SEQ_STR'], 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=7.6)
                    ax.text(x_center, gpu - 0.20, b['LINE3'], 
                            ha='center', va='center', color='#ffd180', fontsize=7.2)
                elif dibujo_dur >= 1500 and rel_w > 0.05:
                    ax.text(x_center, gpu + 0.13, f'Layer {layer} | Calc: {macro_op}', 
                            ha='center', va='center', color='white', fontsize=7.8)
                    ax.text(x_center, gpu - 0.14, b['LINE3'], 
                            ha='center', va='center', color='#ffd180', fontsize=7.2)
                elif rel_w > 0.03:
                    ax.text(x_center, gpu, f'L{layer} | {macro_op}', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=7.5)
            elif label in ['Scatter', 'Gather']:
                net_op = match_network_op(label, b['START_NS'], b['END_NS'], network_ops)
                if net_op and dibujo_dur >= 2000 and rel_w > 0.08:
                    ax.text(x_center, gpu + 0.22, f'Layer {layer} | {net_op["type"]} Nº{net_op["idx"]}', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=8.2)
                    ax.text(x_center, gpu + 0.01, f'PIDs {net_op["min_pid"]}-{net_op["max_pid"]} ({net_op["total_pkts"]} pkts)', 
                            ha='center', va='center', color='#e0f3ff', fontsize=7.2)
                    ax.text(x_center, gpu - 0.20, f'Lat.Mitja: {net_op["avg_flit_lat"]:.1f}c | Prod: {net_op["throughput"]:.2f} flits/c', 
                            ha='center', va='center', color='#ffd180', fontsize=7.2)
                elif net_op and dibujo_dur >= 1500 and rel_w > 0.05:
                    ax.text(x_center, gpu + 0.13, f'Layer {layer} | {net_op["type"]} Nº{net_op["idx"]} ({net_op["total_pkts"]} pkts)', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=7.8)
                    ax.text(x_center, gpu - 0.14, f'Lat: {net_op["avg_flit_lat"]:.1f}c | Prod: {net_op["throughput"]:.2f} f/c', 
                            ha='center', va='center', color='#ffd180', fontsize=7.0)
                elif net_op and dibujo_dur >= 800 and rel_w > 0.03:
                    ax.text(x_center, gpu, f'L{layer} | {net_op["type"]}', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=7.5)
                elif dibujo_dur >= 800 and rel_w > 0.03:
                    ax.text(x_center, gpu, f'L{layer} | {label}', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=7.5)
            elif label == 'Stall':
                if rel_w > 0.06:
                    ax.text(x_center, gpu + 0.12, f'Layer {layer} | Stall', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=7.8)
                    ax.text(x_center, gpu - 0.14, f'Dur: {b["DURATION"]:.0f}ns', 
                            ha='center', va='center', color='#ffcdd2', fontsize=7.0)
                else:
                    ax.text(x_center, gpu, 'Stall', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=7.5)

    ax.set_xlim(start_ns, end_ns)
    ax.set_ylim(-1, num_gpus)
    ax.set_yticks(range(num_gpus))
    ax.set_yticklabels([f'GPU {i}' for i in range(num_gpus)], fontweight='bold')
    ax.set_xlabel('Tiempo Global (Nanosegundos)', fontsize=12, fontweight='bold')
    ax.set_title(f'Cronograma de Ejecución Causal: {start_ns} ns a {end_ns} ns', fontsize=14, fontweight='bold')
    
    legend_elements = [
        Line2D([0], [0], color='#2ca02c', lw=6, label='Cómputo (Calc: Layer {L} | Attention, ExpertFFN...)'),
        Line2D([0], [0], color='#1f77b4', lw=6, label='Red (Layer {L} | Scatter/Gather con PIDs y Flit Metrics)'),
        Line2D([0], [0], color='#d62728', lw=6, label='Bloqueo (Layer {L} | NETWORK_STALL)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9)

    plt.tight_layout()
    filename = f"timeline_part_{window_idx:03d}_{start_ns//1000}k_to_{end_ns//1000}k.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=150)
    plt.close(fig)

def main():
    args = parse_args()
    trc_files = glob.glob(os.path.join(args.folder, "*device_*.trc"))
    if not trc_files:
        print(f"❌ Error: No se encontraron archivos .trc en {args.folder}")
        return

    all_blocks = []
    for file in sorted(trc_files):
        all_blocks.extend(parse_trc_file(file))

    if not all_blocks:
        print(f"❌ Error: No se pudieron extraer datos válidos de los archivos .trc")
        return

    output_dir = os.path.join(args.folder, "cycle-to-cycle")
    os.makedirs(output_dir, exist_ok=True)
    
    network_ops = load_packet_tracking(args.folder)
    if network_ops:
        print(f"📊 Información de red vinculada: {len(network_ops)} operaciones de red encontradas en packet_tracking_debug.csv.")
    
    max_time = int(max(b['END_NS'] for b in all_blocks))
    window_idx = 1
    for start_ns in range(0, max_time + 1, args.window):
        end_ns = start_ns + args.window
        generate_window_plot(all_blocks, start_ns, end_ns, window_idx, output_dir, network_ops)
        window_idx += 1
        
    print(f"✅ Cronogramas enriquecidos generados en: {output_dir}")

if __name__ == "__main__":
    main()