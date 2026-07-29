import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import glob

def parse_args():
    parser = argparse.ArgumentParser(description="Genera el Cronograma Cíclico de las GPUs")
    parser.add_argument("folder", type=str, help="Ruta a la carpeta de resultados (ej. build/results/mixtral...)")
    parser.add_argument("--window", type=int, default=100000, help="Tamaño de la ventana de tiempo en ns por imagen (Por defecto: 100000 ns)")
    return parser.parse_args()

def load_all_trcs(folder):
    """Lee todos los archivos .trc de la carpeta y los une en un solo DataFrame."""
    all_data = []
    trc_files = glob.glob(os.path.join(folder, "*device_*.trc"))
    
    if not trc_files:
        print(f"❌ Error: No se encontraron archivos .trc en {folder}")
        return pd.DataFrame()

    for file in trc_files:
        # Extraer el ID de la GPU del nombre del archivo (ej. TFM_device_0.trc -> 0)
        basename = os.path.basename(file)
        gpu_id = int(basename.split('_')[-1].split('.')[0])
        
        df = pd.read_csv(file, on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        
        # Limpiar datos
        df['GPU'] = gpu_id
        df['START_NS'] = pd.to_numeric(df['START_NS'], errors='coerce')
        df['END_NS'] = pd.to_numeric(df['END_NS'], errors='coerce')
        df['DURATION'] = pd.to_numeric(df['DURATION'], errors='coerce')
        df['TYPE'] = df['TYPE'].str.strip()
        
        # Filtramos eventos de 0 nanosegundos (inicializaciones irrelevantes visualmente)
        df = df[df['DURATION'] > 0]
        all_data.append(df)
        
    return pd.concat(all_data, ignore_index=True)

def get_color_and_label(op_type):
    """Asigna color y una etiqueta corta para que quepa en el bloque."""
    op = op_type.lower()
    if "pop_operation" in op:
        return "#2ca02c", "Calc"  # Verde
    elif "scatter" in op:
        return "#1f77b4", "Scatter" # Azul
    elif "gather" in op:
        return "#1f77b4", "Gather"  # Azul
    elif "stall" in op:
        return "#d62728", "Stall"   # Rojo
    elif "all_reduce" in op:
        return "#17becf", "AllRed"  # Cyan
    else:
        return "#7f7f7f", op[:6]    # Gris por defecto

def generate_window_plot(df, start_ns, end_ns, window_idx, output_dir):
    """Genera una sola imagen del cronograma para el rango de tiempo dado."""
    # Filtrar eventos que se solapan (intersectan) con esta ventana de tiempo
    mask = (df['START_NS'] < end_ns) & (df['END_NS'] > start_ns)
    df_window = df[mask]
    
    if df_window.empty:
        return # Si no hay nada en este tiempo, no generamos imagen vacía

    num_gpus = int(df['GPU'].max()) + 1
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Dibujar la cuadrícula horizontal para cada GPU
    for i in range(num_gpus):
        ax.axhline(i, color='gray', linestyle=':', alpha=0.3)

    # Dibujar cada bloque
    for _, row in df_window.iterrows():
        gpu = row['GPU']
        op_start = row['START_NS']
        op_end = row['END_NS']
        op_type = row['TYPE']
        
        # Recortar el bloque para que no se salga de los límites de la ventana actual
        dibujo_start = max(start_ns, op_start)
        dibujo_end = min(end_ns, op_end)
        dibujo_duration = dibujo_end - dibujo_start
        
        color, label = get_color_and_label(op_type)
        
        # Crear rectángulo
        rect = patches.Rectangle((dibujo_start, gpu - 0.4), dibujo_duration, 0.8, 
                                 linewidth=1, edgecolor='black', facecolor=color, alpha=0.8)
        ax.add_patch(rect)
        
        # Poner etiqueta de texto si el bloque es suficientemente ancho (>3% de la ventana)
        if dibujo_duration / (end_ns - start_ns) > 0.03:
            x_center = dibujo_start + (dibujo_duration / 2)
            ax.text(x_center, gpu, label, ha='center', va='center', 
                    color='white', fontweight='bold', fontsize=9)

    ax.set_xlim(start_ns, end_ns)
    ax.set_ylim(-1, num_gpus)
    ax.set_yticks(range(num_gpus))
    ax.set_yticklabels([f'GPU {i}' for i in range(num_gpus)], fontweight='bold')
    
    # Formateo de títulos
    ax.set_xlabel('Tiempo Global (Nanosegundos)', fontsize=12, fontweight='bold')
    ax.set_title(f'Cronograma de Ejecución: {start_ns} ns a {end_ns} ns', fontsize=14)
    
    # Leyenda personalizada manual
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#2ca02c', lw=6, label='Cómputo (POP_OPERATION)'),
        Line2D([0], [0], color='#1f77b4', lw=6, label='Red (MoE Scatter/Gather)'),
        Line2D([0], [0], color='#d62728', lw=6, label='Bloqueo (NETWORK_STALL)')
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    # Guardar
    plt.tight_layout()
    filename = f"timeline_part_{window_idx:03d}_{start_ns//1000}k_to_{end_ns//1000}k.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=150)
    plt.close(fig)

def main():
    args = parse_args()
    
    df = load_all_trcs(args.folder)
    if df.empty:
        return

    # Crear el directorio cycle-to-cycle
    output_dir = os.path.join(args.folder, "cycle-to-cycle")
    os.makedirs(output_dir, exist_ok=True)
    
    # Calcular el tiempo total simulado
    max_time = int(df['END_NS'].max())
    print(f"📊 Tiempo total simulado: {max_time} ns.")
    print(f"📸 Generando imágenes con ventanas de {args.window} ns...")
    
    window_idx = 1
    generated_count = 0
    
    # Bucle deslizando la ventana de tiempo
    for start_ns in range(0, max_time + 1, args.window):
        end_ns = start_ns + args.window
        
        # Solo generamos la ventana si hay eventos que se solapan en este tramo
        mask = (df['START_NS'] < end_ns) & (df['END_NS'] > start_ns)
        if df[mask].empty:
            continue # Saltar ventanas en blanco (por si acaso)
            
        generate_window_plot(df, start_ns, end_ns, window_idx, output_dir)
        generated_count += 1
        window_idx += 1

    print(f"✅ ¡Completado! Se han generado {generated_count} imágenes en:")
    print(f"📁 {output_dir}")

if __name__ == "__main__":
    main()