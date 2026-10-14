import argparse
import subprocess
import os
import shutil
import sys
import math
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="LLM + BookSim2 Co-Simulation Runner")
    # Opciones de Modelo
    parser.add_argument("--model", type=str, default="mixtral", help="Target LLM Model")
    
    # Opciones de Red Espacial (BookSim2)
    parser.add_argument("--topology", type=str, default="torus", choices=["mesh", "torus", "ring"], help="BookSim2 Topology")
    parser.add_argument("--net_dims", type=int, nargs='+', default=[8], help="Network dimensions (e.g., '4 4' for 4x4, or '8' for 1D)")
    parser.add_argument("--vcs", type=int, default=4, help="Number of Virtual Channels (VCs)")
    parser.add_argument("--routing", type=str, default="dim_order", choices=["dim_order", "min_adapt"], help="Routing algorithm")
    
    # Opciones de Carga de Trabajo (LLMSimulator Workload)
    parser.add_argument("--input_len", type=int, default=1024, help="Prompt size (Prefill tokens)")
    parser.add_argument("--output_len", type=int, default=10, help="Number of tokens to generate per iteration (Decoding steps)")
    parser.add_argument("--iter", type=int, default=5, help="Number of statistical iterations to run")
    parser.add_argument("--batch_size", type=int, default=32, help="Max batch size for continuous batching")
    
    # Opciones de Simulación
    parser.add_argument("--parallel", action="store_true", help="Enable parallel_execution (xPU + PIM overlapping)")
    parser.add_argument("--data_mode", type=str, default="synthesis", help="Data mode (e.g., synthesis, analytical)")
    parser.add_argument("--gantt", action="store_true", help="Export Gantt charts")

    # Opciones de Debugging
    parser.add_argument("--debug_pids", action="store_true", help="Genera el CSV de ciclo de vida de los paquetes (Gantt)")
    
    return parser.parse_args()

def generate_configs(args, output_dir, total_devices):
    n_dims = len(args.net_dims)
    
    # BookSim2 solo acepta redes simétricas (k entero). Tomamos el primer valor.
    k_str = str(args.net_dims[0])
    
    booksim_cfg_path = os.path.join(output_dir, "test.cfg")
    with open(booksim_cfg_path, "w") as f:
        f.write(f"topology = {args.topology};\n")
        f.write(f"k = {k_str};\n")
        f.write(f"n = {n_dims};\n")
        f.write(f"routing_function = {args.routing};\n")
        f.write(f"num_vcs = {args.vcs};\n")
        f.write(f"injection_rate = 0.0;\n")

    parallel_str = "on" if args.parallel else "off"
    gantt_str = "on" if args.gantt else "off"

    # Plantilla YAML inyectando las nuevas variables de carga de trabajo
    yaml_content = f"""model:
  model_name: {args.model}

system:
  gpu_gen: B100
  nvlink_gen: 5
  infiniband_gen: 800
  num_node: 1
  num_device: {total_devices}
  processor_type: GPU
  distribution:
    expert_tensor_degree: 1
    none_expert_tensor_degree: 1
  optimization:
    parallel_execution: {parallel_str}
    hetero_subbatch: off
    disagg_system: off
    use_low_unit_moe_only: off
    use_ramulator: off
    compressed_kv: on
    use_absorb: on
    use_flash_mla: on
    use_flash_attention: on
    reuse_kv_cache: on
    kv_cache_reuse_rate: 0.0
    prefill_mode: off
    decode_mode: on

serving:
  max_batch_size: {args.batch_size}
  max_process_token: 0

simulation:
  data: {args.data_mode}
  input_len: {args.input_len}
  output_len: {args.output_len}
  precision_byte: 1
  skewness: 0.0
  iter: {args.iter}
  injection_rate: 0
  exit_out_of_memory: off
  mem_cap_limit: off

log:
  print_log: on
  export_gantt: {gantt_str}
  output_directory: {output_dir}/
  gantt_directory: {output_dir}/gantt/
"""
    
    llm_cfg_path = os.path.join(output_dir, "config.yaml")
    with open(llm_cfg_path, "w") as f:
        f.write(yaml_content)
        
    return llm_cfg_path, booksim_cfg_path

def main():
    if not os.path.exists("build/run"):
        print("❌ Error: Ejecutable 'build/run' no encontrado.")
        sys.exit(1)

    args = parse_args()
    total_devices = math.prod(args.net_dims)
    
    # ==========================================
    # GUARDARRAÍLES DE ARQUITECTURA
    # ==========================================
    if args.topology == "torus" and args.vcs < 2:
        print("🛑 ERROR CRÍTICO DE ARQUITECTURA:")
        print("   La topología Torus requiere al menos 2 VCs (num_vcs >= 2).")
        sys.exit(1)
        
    if not all(dim == args.net_dims[0] for dim in args.net_dims):
        print("🛑 ERROR DE ARQUITECTURA (BookSim2 Limit):")
        print("   BookSim2 solo soporta mallas/toros SIMÉTRICOS usando k y n.")
        print("   Todas las dimensiones deben ser iguales (ej. 4 4, no 4 2).")
        sys.exit(1)
        
    if total_devices > 256:
        print("⚠️ ADVERTENCIA DE LÍMITE FÍSICO:")
        print(f"   Estás intentando simular {total_devices} GPUs. BookSim2 escalará cuadráticamente.")
        
    # EL TIP PRO: Advertencia de Tiempo de Simulación
    total_tokens_simulados = args.output_len * args.iter
    if total_tokens_simulados > 150:
        print("\n⏳ ⚠️ ADVERTENCIA DE RENDIMIENTO (Sobrecarga de Red):")
        print(f"   Estás solicitando {args.output_len} tokens x {args.iter} iteraciones = {total_tokens_simulados} pasos de decodificación.")
        print("   Como la red es ciclo a ciclo (Cycle-Accurate), esto va a inyectar una cantidad masiva de eventos.")
        print("   La simulación podría tardar varios minutos. ¡Paciencia!")
    # ==========================================

    # --- INYECTAR MODO DEBUG PARA C++ ---
    if args.debug_pids:
        os.environ["SIM_DEBUG_PIDS"] = "1"
    else:
        os.environ.pop("SIM_DEBUG_PIDS", None)
    # ------------------------------------

    dims_str = "x".join(map(str, args.net_dims))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Nuevo naming basado en Batch Size
    folder_name = f"{args.model}_{dims_str}dev_{args.topology}_bs{args.batch_size}_{timestamp}"
    output_dir = os.path.join("build", "results", folder_name)
    os.makedirs(os.path.join(output_dir, "gantt"), exist_ok=True)
    
    llm_cfg, booksim_cfg = generate_configs(args, output_dir, total_devices)
    
    shutil.copy(booksim_cfg, "test.cfg")
    shutil.copy(llm_cfg, "config.yaml")
    
    cmd_str = " ".join(sys.argv)
    executable = ["./build/run"]
    log_file_path = os.path.join(output_dir, "sim_output.txt")
    
    print(f"\n🚀 Iniciando Co-Simulación...")
    print(f"🖥️ Red: {dims_str} {args.topology.upper()} | VCs: {args.vcs} | Enrutamiento: {args.routing}")
    print(f"🧠 Concurrencia: Batch Size {args.batch_size} (Max. secuencias simultáneas)")
    print(f"🔄 Estadística: {args.iter} Iteraciones (Trazas pre-cargadas de 10 tokens)")
    print(f"📁 Resultados irán a: {output_dir}")
    print(f"⚙️ Comando: {cmd_str}\n" + "-"*40)
    
    track_pids_data = []  # Almacenaje en memoria de las trazas de paquetes
    
    with open(log_file_path, "w") as log_file:
        log_file.write(f"COMMAND EXECUTED: python {cmd_str}\n")
        log_file.write("-" * 50 + "\n")
        log_file.flush()
        
        process = subprocess.Popen(executable, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        for line in process.stdout:
            # Interceptamos la traza mágica de BookSim2
            if line.startswith("[TRACK_PID]"):
                track_pids_data.append(line.strip().replace("[TRACK_PID] ", ""))
            else:
                sys.stdout.write(line)
                log_file.write(line)
            
        process.wait()
            
    print(f"\n📦 Recolectando archivos .trc generados...")
    moved_trcs = 0
    for file in os.listdir("."):
        if file.endswith(".trc"):
            shutil.move(file, os.path.join(output_dir, file))
            moved_trcs += 1
            
    print(f"✅ Simulación terminada. Se movieron {moved_trcs} archivos .trc. Datos sellados en: {output_dir}")

    # Escribir el CSV del Tracking si estábamos en Debug Mode
    if args.debug_pids and track_pids_data:
        csv_path = os.path.join(output_dir, "packet_tracking_debug.csv")
        with open(csv_path, "w") as f:
            f.write("PID,Source,Dest,Creation_Cycle,Inject_Cycle,Receive_Cycle,Total_Latency,Network_Latency,Queueing_Delay,Num_Flits,Size_Bytes\n")
            f.write("\n".join(track_pids_data))
        print(f"🐛 Trazas PID (Modo Debug) guardadas en: {csv_path}\n")

    else:
        print("")

if __name__ == "__main__":
    main()