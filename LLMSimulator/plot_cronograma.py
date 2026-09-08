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

def get_color_and_label(op_type):
    op = op_type.lower()
    if "pop_operation" in op:
        return "#2ca02c", "Calc"
    elif "scatter" in op:
        return "#1f77b4", "Scatter"
    elif "gather" in op:
        return "#1f77b4", "Gather"
    elif "stall" in op:
        return "#d62728", "Stall"
    elif "all_reduce" in op:
        return "#17becf", "AllRed"
    return "#7f7f7f", op[:6]

def generate_window_plot(df, start_ns, end_ns, window_idx, output_dir):
    mask = (df['START_NS'] < end_ns) & (df['END_NS'] > start_ns)
    df_window = df[mask].copy()
    if df_window.empty: return

    # Fusión Algorítmica de Eventos (Coalescing)
    df_window = df_window.sort_values(by=['GPU', 'START_NS']).reset_index(drop=True)
    df_window['group'] = ((df_window['TYPE'] != df_window['TYPE'].shift(1)) | 
                          (df_window['GPU'] != df_window['GPU'].shift(1))).cumsum()
    
    df_merged = df_window.groupby(['GPU', 'TYPE', 'group'], as_index=False).agg(
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
        color, label = get_color_and_label(row['TYPE'])
        
        # Alpha=1.0 para colores puros, sin borde intermedio
        rect = patches.Rectangle((dibujo_start, gpu - 0.4), dibujo_duration, 0.8, 
                                 linewidth=0.5, edgecolor='black', facecolor=color, alpha=1.0)
        ax.add_patch(rect)
        
        # Etiqueta única centralizada
        if dibujo_duration / (end_ns - start_ns) > 0.03:
            x_center = dibujo_start + (dibujo_duration / 2)
            ax.text(x_center, gpu, label, ha='center', va='center', 
                    color='white', fontweight='bold', fontsize=9)

    ax.set_xlim(start_ns, end_ns)
    ax.set_ylim(-1, num_gpus)
    ax.set_yticks(range(num_gpus))
    ax.set_yticklabels([f'GPU {i}' for i in range(num_gpus)], fontweight='bold')
    ax.set_xlabel('Tiempo Global (Nanosegundos)', fontsize=12, fontweight='bold')
    ax.set_title(f'Cronograma de Ejecución Causal: {start_ns} ns a {end_ns} ns', fontsize=14)
    
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#2ca02c', lw=6, label='Cómputo (POP_OPERATION)'),
        Line2D([0], [0], color='#1f77b4', lw=6, label='Red (MoE Scatter/Gather)'),
        Line2D([0], [0], color='#d62728', lw=6, label='Bloqueo (NETWORK_STALL)')
    ]
    ax.legend(handles=legend_elements, loc='upper right')

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
    
    max_time = int(df['END_NS'].max())
    window_idx = 1
    for start_ns in range(0, max_time + 1, args.window):
        end_ns = start_ns + args.window
        mask = (df['START_NS'] < end_ns) & (df['END_NS'] > start_ns)
        if not df[mask].empty:
            generate_window_plot(df, start_ns, end_ns, window_idx, output_dir)
            window_idx += 1

if __name__ == "__main__":
    main()