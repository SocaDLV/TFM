import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="TFM Phase 5: Trace Analyzer")
    parser.add_argument("--recent", type=int, default=3, help="Número de ejecuciones más recientes a analizar (por defecto: 3)")
    parser.add_argument("--model", type=str, default=None, help="Filtrar por modelo (ej. mixtral)")
    parser.add_argument("--today", action="store_true", help="Analizar solo las ejecuciones del día de hoy")
    parser.add_argument("--dir", type=str, default="build/results", help="Directorio base de los resultados")
    return parser.parse_args()

def get_target_folders(args):
    """Busca, filtra y ordena las carpetas de resultados."""
    if not os.path.exists(args.dir):
        print(f"❌ Error: El directorio {args.dir} no existe.")
        return []

    folders = []
    today_str = datetime.now().strftime("%Y%m%d")

    for f in os.listdir(args.dir):
        path = os.path.join(args.dir, f)
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
    return [item for item in folders[:args.recent]]

def analyze_folder(folder_path, folder_name):
    """Extrae métricas precisas del archivo .trc"""
    compute_total = 0
    transit_total = 0
    stall_total = 0
    scatter_total = 0
    gather_total = 0
    devices_counted = 0

    for file in os.listdir(folder_path):
        if file.endswith(".trc") and "device" in file.lower():
            filepath = os.path.join(folder_path, file)
            df = pd.read_csv(filepath, on_bad_lines='skip')
            df.columns = df.columns.str.strip()
            df['TYPE'] = df['TYPE'].str.strip() # Limpiar espacios
            df['DURATION'] = pd.to_numeric(df['DURATION'], errors='coerce').fillna(0)
            
            # 1. Network Transit (Tiempo de viaje de los datos en BookSim2)
            scatter = df[df['TYPE'].str.contains('scatter', case=False, na=False)]['DURATION'].sum()
            gather = df[df['TYPE'].str.contains('gather', case=False, na=False)]['DURATION'].sum()
            all_reduce = df[df['TYPE'].str.contains('all_reduce', case=False, na=False)]['DURATION'].sum()
            transit = scatter + gather + all_reduce
            
            # 2. Synchronization Stalls (Tiempo de inactividad por desbalanceo)
            stall = df[df['TYPE'].str.contains('stall', case=False, na=False)]['DURATION'].sum()

            # 3. Compute Time (Operaciones matemáticas en la GPU: compatible con POP_OPERATION y nombres reales)
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

    return {
        'Configuración': folder_name,
        'Compute Time (ns)': compute_total / devices_counted,
        'Network Transit Time (ns)': transit_total / devices_counted,
        'Network Stalls (ns)': stall_total / devices_counted,
        'MoE Scatter (ns)': scatter_total / devices_counted,
        'MoE Gather (ns)': gather_total / devices_counted
    }

def main():
    args = parse_args()
    target_folders = get_target_folders(args)

    if not target_folders:
        print("⚠️ No se encontraron resultados que coincidan con los filtros.")
        return

    print(f"📊 Fase 5: Analizando las {len(target_folders)} ejecuciones seleccionadas...")
    
    results = []
    for _, folder_path, folder_name in target_folders:
        short_label = "_".join(folder_name.split('_')[:-2]) 
        stats = analyze_folder(folder_path, short_label)
        if stats:
            results.append(stats)

    if not results:
        print("❌ No se encontraron archivos .trc válidos en las carpetas seleccionadas.")
        return

    results.reverse() 
    df = pd.DataFrame(results)
    df.set_index('Configuración', inplace=True)
    
    # Crear la subcarpeta con marca de tiempo para este análisis
    timestamp_analisis = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("build", "analysis", f"analisis_{timestamp_analisis}")
    os.makedirs(output_dir, exist_ok=True)
    
    # --- GRÁFICA 1: La Anatomía de la Latencia ---
    fig, ax = plt.subplots(figsize=(12, 7))
    df[['Compute Time (ns)', 'Network Transit Time (ns)', 'Network Stalls (ns)']].plot(
        kind='bar', stacked=True, color=['#2ca02c', '#1f77b4', '#d62728'], ax=ax
    )
    plt.title('TFM: Anatomía de Latencia por Dispositivo (Cómputo vs Red vs Stalls)', fontsize=14)
    plt.ylabel('Tiempo Medio por GPU (nanosegundos)', fontsize=12)
    plt.xlabel('Configuración de Red / Tokens', fontsize=12)
    plt.xticks(rotation=15, ha='right')
    plt.legend(["Compute Time (Procesamiento GPU)", "Network Transit (Viaje por BookSim2)", "Network Stalls (Espera de Sincronización)"])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    plot1_path = os.path.join(output_dir, "anatomia_latencia.png")
    plt.savefig(plot1_path, dpi=300)
    
    # --- GRÁFICA 2: Desglose MoE ---
    fig2, ax2 = plt.subplots(figsize=(12, 7))
    df[['MoE Scatter (ns)', 'MoE Gather (ns)']].plot(
        kind='bar', color=['#1f77b4', '#ff7f0e'], ax=ax2
    )
    plt.title('TFM: Coste de las Primitivas de Red MoE (Scatter vs Gather)', fontsize=14)
    plt.ylabel('Tiempo Medio por GPU (nanosegundos)', fontsize=12)
    plt.xlabel('Configuración de Red / Tokens', fontsize=12)
    plt.xticks(rotation=15, ha='right')
    plt.legend(["MoE Scatter (Distribución a Expertos)", "MoE Gather (Recolección de Resultados)"])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    plot2_path = os.path.join(output_dir, "desglose_primitivas_moe.png")
    plt.savefig(plot2_path, dpi=300)

    print(f"\n✅ Análisis completado con éxito.")
    print(f"📦 Gráficas guardadas en el directorio: {output_dir}")

if __name__ == "__main__":
    main()