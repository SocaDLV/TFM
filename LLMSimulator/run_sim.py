import argparse
import subprocess
import os
import shutil
import sys
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="LLM + BookSim2 Co-Simulation Runner")
    # Opciones de Hardware
    parser.add_argument("--model", type=str, default="mixtral", help="Target LLM Model")
    parser.add_argument("--devices", type=int, default=8, help="Number of GPUs")
    parser.add_argument("--topology", type=str, default="torus", choices=["mesh", "torus", "ring"], help="BookSim2 Topology")
    
    # Opciones de Simulación
    parser.add_argument("--parallel", action="store_true", help="Enable parallel_execution (xPU + PIM overlapping)")
    parser.add_argument("--data_mode", type=str, default="synthesis", help="Data mode (e.g., synthesis, analytical)")
    parser.add_argument("--gantt", action="store_true", help="Export Gantt charts")
    
    return parser.parse_args()

def generate_configs(args, output_dir):
    # 1. Crear configuración para BookSim2
    booksim_cfg_path = os.path.join(output_dir, "test.cfg")
    with open(booksim_cfg_path, "w") as f:
        f.write(f"topology = {args.topology};\n")
        f.write(f"k = {args.devices};\n")
        f.write(f"n = 1;\n")
        f.write(f"routing_function = dim_order;\n")
        f.write(f"num_vcs = 4;\n")
        f.write(f"injection_rate = 0.0;\n")

    # Transformar booleanos a "on"/"off" sin comillas
    parallel_str = "on" if args.parallel else "off"
    gantt_str = "on" if args.gantt else "off"

    # 2. Crear configuración YAML manualmente para evitar las comillas de pyyaml
    yaml_content = f"""model:
  model_name: {args.model}

system:
  gpu_gen: B100
  nvlink_gen: 5
  infiniband_gen: 800
  num_node: 1
  num_device: {args.devices}
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
  max_batch_size: 32
  max_process_token: 0

simulation:
  data: {args.data_mode}
  input_len: 1024
  output_len: 10
  precision_byte: 1
  skewness: 0.0
  iter: 5
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
    # Comprobación de seguridad: Asegurar que estamos en la raíz del proyecto
    if not os.path.exists("build/run"):
        print("❌ Error: Ejecutable 'build/run' no encontrado.")
        print("👉 Asegúrate de ejecutar este script desde la RAÍZ de LLMSimulator (no desde dentro de 'build/').")
        sys.exit(1)

    args = parse_args()
    
    # Nombrado científico de la carpeta de resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{args.model}_{args.devices}dev_{args.topology}_par{args.parallel}_{timestamp}"
    output_dir = os.path.join("build", "results", folder_name)
    os.makedirs(os.path.join(output_dir, "gantt"), exist_ok=True)
    
    llm_cfg, booksim_cfg = generate_configs(args, output_dir)
    
    # Copiar configs a donde el ejecutable en C++ los espera leer (en la raíz)
    shutil.copy(booksim_cfg, "test.cfg")
    shutil.copy(llm_cfg, "config.yaml")
    
    cmd_str = " ".join(sys.argv)
    executable = ["./build/run"]
    
    log_file_path = os.path.join(output_dir, "sim_output.txt")
    
    print(f"\n🚀 Iniciando Co-Simulación...")
    print(f"📁 Resultados irán a: {output_dir}")
    print(f"⚙️ Comando: {cmd_str}\n" + "-"*40)
    
    with open(log_file_path, "w") as log_file:
        log_file.write(f"COMMAND EXECUTED: python {cmd_str}\n")
        log_file.write("-" * 50 + "\n")
        log_file.flush()
        
        process = subprocess.Popen(executable, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        for line in process.stdout:
            sys.stdout.write(line)
            log_file.write(line)
            
        process.wait()
            
    # --- AÑADIR ESTE BLOQUE ---
    print(f"\n📦 Recolectando archivos .trc generados...")
    moved_trcs = 0
    for file in os.listdir("."):  # Busca en la raíz del proyecto
        if file.endswith(".trc"):
            shutil.move(file, os.path.join(output_dir, file))
            moved_trcs += 1
    # --------------------------
            
    print(f"✅ Simulación terminada. Se movieron {moved_trcs} archivos .trc. Datos sellados en: {output_dir}\n")

if __name__ == "__main__":
    main()
            
