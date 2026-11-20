# -*- coding: utf-8 -*-
"""
Simulation Runner for LLM-NoC Co-Simulation Workbench.
Handles background process execution, staging directory management,
configuration generation (config.yaml, test.cfg, AnyNet), real-time log
interception, [TRACK_PID] CSV capture, progress tracking, and abort control.
"""

import os
import sys
import shutil
import subprocess
import threading
import time
import math
import re
from datetime import datetime
from pathlib import Path


class SimulationRunner:
    """Manages the lifecycle of a simulation execution in staging."""

    def __init__(self, base_dir=None):
        if base_dir is None:
            # LLMSimulator/
            self.base_dir = Path(__file__).resolve().parent.parent
        else:
            self.base_dir = Path(base_dir).resolve()

        self.build_dir = self.base_dir / "build"
        self.staging_root = self.build_dir / "tmp_staging"

        self.lock = threading.Lock()
        self.status = "idle"  # idle, running, completed, error, aborted
        self.current_process = None
        self.worker_thread = None
        self.aborted = False

        self.staging_folder_name = None
        self.staging_dir = None
        self.start_time = None
        self.end_time = None
        self.elapsed_seconds = 0.0

        self.progress_percent = 0
        self.progress_detail = ""
        self.log_lines = []
        self.error_message = None

        self.current_params = {}

        # Detect model layer counts for progress estimation
        self.model_layers = {
            "mixtral": 32,
            "deepseekv3": 60,
            "deepseek": 60,
            "llama": 32,
            "llama7bmoe": 32,
            "openmoe": 32,
            "grok1": 64,
            "glam": 32,
            "llama3_405b": 126,
            "llama4_scout": 48,
            "llama4_maverick": 48
        }

    def get_status(self, offset=0):
        """Thread-safe status inspection with incremental log retrieval."""
        with self.lock:
            if self.status == "running" and self.start_time is not None:
                elapsed = time.time() - self.start_time
            else:
                elapsed = self.elapsed_seconds

            total_lines = len(self.log_lines)
            safe_offset = max(0, min(offset, total_lines))
            new_logs = self.log_lines[safe_offset:]

            return {
                "status": self.status,
                "staging_folder_name": self.staging_folder_name,
                "staging_dir": str(self.staging_dir) if self.staging_dir else None,
                "elapsed_seconds": round(elapsed, 1),
                "progress_percent": self.progress_percent,
                "progress_detail": self.progress_detail,
                "log_offset": total_lines,
                "logs": new_logs,
                "error_message": self.error_message,
                "params": self.current_params
            }

    def validate_params(self, params):
        """Validates configuration parameters against microarchitectural guardrails."""
        model = str(params.get("model", "mixtral")).strip()
        if model.lower() in ["deepseek", "deepseekv3", "deepseek-v3", "deepseek_v3"]:
            model = "deepseekV3"
        elif model.lower() in ["mixtral", "mixtral8x7b", "mixtral_8x7b"]:
            model = "mixtral"

        net_dims = params.get("net_dims", [8])
        if isinstance(net_dims, str):
            net_dims = [int(x) for x in re.findall(r"\d+", net_dims)]
        if not net_dims:
            net_dims = [8]

        total_devices = math.prod(net_dims)
        topology = str(params.get("topology", "torus")).lower().strip()
        vcs = int(params.get("vcs", 4))
        tensor_degree = int(params.get("tensor_degree", 1))

        # Guardrail 1: Torus deadlock prevention
        if topology == "torus" and vcs < 2:
            raise ValueError(
                "Riesgo de deadlock microarquitectural: La topología Toro con enrutamiento "
                "Dateline requiere obligatoriamente al menos 2 canales virtuales (vcs >= 2) "
                "para romper ciclos en el Grafo de Dependencia de Canales (CDG)."
            )

        # Guardrail 2: Topology symmetry check
        n_dims = len(net_dims)
        if not all(d == net_dims[0] for d in net_dims):
            if not (topology == "mesh" and n_dims == 2):
                raise ValueError(
                    f"Topología asimétrica no soportada: {net_dims} para '{topology}'. "
                    "BookSim2 solo soporta topologías regulares simétricas (k^n) o mallas 2D "
                    "asimétricas gestionadas mediante AnyNet (ej. '4 2' con mesh)."
                )

        # Guardrail 3: Tensor parallelism divisibility
        if total_devices % tensor_degree != 0:
            raise ValueError(
                f"Error de particionamiento: El número total de GPUs ({total_devices}) "
                f"debe ser divisible por el grado de Tensor Parallelism ({tensor_degree})."
            )

        # Guardrail 4: Mixtral expert partitioning limit
        if model.lower() == "mixtral" and total_devices > 8:
            raise ValueError(
                f"Límite de paralelismo excedido: Mixtral 8x7B contiene 8 expertos MoE; "
                f"LLMSimulator no soporta particionar expertos entre más de 8 GPUs ({total_devices} solicitadas)."
            )

        return {
            "model": model,
            "net_dims": net_dims,
            "total_devices": total_devices,
            "topology": topology,
            "vcs": vcs,
            "routing": str(params.get("routing", "dim_order")).strip(),
            "batch_size": int(params.get("batch_size", 32)),
            "input_len": int(params.get("input_len", 1024)),
            "output_len": int(params.get("output_len", 2)),
            "iter": int(params.get("iter", 2)),
            "tensor_degree": tensor_degree,
            "skewness": float(params.get("skewness", 0.0)),
            "gpu_gen": str(params.get("gpu_gen", "B100")).strip(),
            "data_mode": str(params.get("data_mode", "synthesis")).strip(),
            "parallel": bool(params.get("parallel", False)),
            "gantt": bool(params.get("gantt", False)),
            "debug_pids": bool(params.get("debug_pids", True))
        }

    def run(self, raw_params):
        """Starts simulation asynchronously in a background thread."""
        with self.lock:
            if self.status == "running":
                raise RuntimeError("Ya hay una simulación en ejecución. Abórtala antes de lanzar otra.")

            validated = self.validate_params(raw_params)
            self.current_params = validated
            self.status = "running"
            self.aborted = False
            self.progress_percent = 0
            self.progress_detail = "Iniciando entorno de simulación..."
            self.log_lines = []
            self.error_message = None
            self.start_time = time.time()
            self.end_time = None
            self.elapsed_seconds = 0.0

            self.worker_thread = threading.Thread(
                target=self._execution_worker,
                args=(validated,),
                daemon=True
            )
            self.worker_thread.start()

            return {
                "status": "running",
                "staging_folder_name": self.staging_folder_name
            }

    def abort(self):
        """Terminates the current simulation cleanly."""
        with self.lock:
            if self.status != "running" or not self.current_process:
                return {"status": self.status}

            self.aborted = True
            self.log_lines.append("\n🛑 Señal de aborto recibida. Terminando subproceso ./build/run...")

            try:
                self.current_process.terminate()
            except Exception as e:
                self.log_lines.append(f"⚠️ Error al terminar proceso: {e}")

        # Wait briefly for process to exit
        time.sleep(1.0)
        with self.lock:
            if self.current_process and self.current_process.poll() is None:
                try:
                    self.current_process.kill()
                    self.log_lines.append("🛑 Proceso forzado a finalizar (kill).")
                except Exception:
                    pass

            self.status = "aborted"
            if self.start_time:
                self.elapsed_seconds = time.time() - self.start_time
            self.progress_detail = "Simulación abortada por el usuario."

        return {"status": "aborted"}

    def _generate_configs(self, params, target_dir):
        """Generates test.cfg, AnyNet files (if asymmetric mesh), and config.yaml."""
        net_dims = params["net_dims"]
        n_dims = len(net_dims)
        total_devices = params["total_devices"]
        topology = params["topology"]
        vcs = params["vcs"]
        routing = params["routing"]

        booksim_cfg_path = target_dir / "test.cfg"
        anynet_local_copy = None

        # Soporte nativo para mallas 2D asimétricas mediante AnyNet
        if topology == "mesh" and n_dims == 2 and net_dims[0] != net_dims[1]:
            d0, d1 = net_dims[0], net_dims[1]
            anynet_filename = f"mesh_{d0}x{d1}.txt"
            anynet_file_path = (target_dir / anynet_filename).resolve()

            with open(anynet_file_path, "w", encoding="utf-8") as af:
                for r in range(d0):
                    for c in range(d1):
                        node_id = r * d1 + c
                        neighbors = []
                        if r > 0:
                            neighbors.append(f"router {(r - 1) * d1 + c}")
                        if r < d0 - 1:
                            neighbors.append(f"router {(r + 1) * d1 + c}")
                        if c > 0:
                            neighbors.append(f"router {r * d1 + (c - 1)}")
                        if c < d1 - 1:
                            neighbors.append(f"router {r * d1 + (c + 1)}")
                        af.write(f"router {node_id} node {node_id} " + " ".join(neighbors) + "\n")

            # Copiar también en la raíz base de LLMSimulator para compatibilidad directa
            anynet_local_copy = self.base_dir / anynet_filename
            shutil.copy(anynet_file_path, anynet_local_copy)

            with open(booksim_cfg_path, "w", encoding="utf-8") as f:
                f.write(f"// Topologia Malla 2D Asimetrica ({d0}x{d1} = {total_devices} nodos)\n")
                f.write("topology = anynet;\n")
                f.write(f"network_file = {anynet_file_path};\n")
                f.write("routing_function = min;\n")
                f.write(f"num_vcs = {vcs};\n")
                f.write("injection_rate = 0.0;\n")
        else:
            k_str = str(net_dims[0])
            with open(booksim_cfg_path, "w", encoding="utf-8") as f:
                f.write(f"topology = {topology};\n")
                f.write(f"k = {k_str};\n")
                f.write(f"n = {n_dims};\n")
                f.write(f"routing_function = {routing};\n")
                f.write(f"num_vcs = {vcs};\n")
                f.write("injection_rate = 0.0;\n")

        parallel_str = "on" if params["parallel"] else "off"
        gantt_str = "on" if params["gantt"] else "off"

        yaml_content = f"""model:
  model_name: {params["model"]}

system:
  gpu_gen: {params["gpu_gen"]}
  nvlink_gen: 5
  infiniband_gen: 800
  num_node: 1
  num_device: {total_devices}
  processor_type: GPU
  distribution:
    expert_tensor_degree: 1
    none_expert_tensor_degree: {params["tensor_degree"]}
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
  max_batch_size: {params["batch_size"]}
  max_process_token: 0

simulation:
  data: {params["data_mode"]}
  input_len: {params["input_len"]}
  output_len: {params["output_len"]}
  precision_byte: 1
  skewness: {params["skewness"]}
  iter: {params["iter"]}
  injection_rate: 0
  exit_out_of_memory: off
  mem_cap_limit: off

log:
  print_log: on
  export_gantt: {gantt_str}
  output_directory: {target_dir}/
  gantt_directory: {target_dir}/gantt/
"""
        llm_cfg_path = target_dir / "config.yaml"
        with open(llm_cfg_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        # Copiar config.yaml y test.cfg al directorio de trabajo base de LLMSimulator
        shutil.copy(booksim_cfg_path, self.base_dir / "test.cfg")
        shutil.copy(llm_cfg_path, self.base_dir / "config.yaml")

        return llm_cfg_path, booksim_cfg_path

    def _execution_worker(self, params):
        """Worker thread executing the binary in staging."""
        executable = self.build_dir / "run"
        if not executable.exists() or not os.access(executable, os.X_OK):
            with self.lock:
                self.status = "error"
                self.error_message = f"Ejecutable no encontrado o sin permisos de ejecución: {executable}"
                self.log_lines.append(f"❌ Error: {self.error_message}")
                return

        try:
            # 1. Preparar directorio temporal en build/tmp_staging/
            if self.staging_root.exists():
                try:
                    shutil.rmtree(self.staging_root)
                except Exception as e:
                    pass

            self.staging_root.mkdir(parents=True, exist_ok=True)

            dims_str = "x".join(map(str, params["net_dims"]))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tp_suffix = f"_tp{params['tensor_degree']}" if params["tensor_degree"] > 1 else ""
            skew_suffix = f"_skew{params['skewness']}" if params["skewness"] > 0.0 else ""
            folder_name = (
                f"{params['model']}_{dims_str}dev_{params['topology']}"
                f"{tp_suffix}_bs{params['batch_size']}{skew_suffix}_{timestamp}"
            )

            staging_dir = self.staging_root / folder_name
            staging_dir.mkdir(parents=True, exist_ok=True)
            (staging_dir / "gantt").mkdir(parents=True, exist_ok=True)

            with self.lock:
                self.staging_folder_name = folder_name
                self.staging_dir = staging_dir

            # 2. Generar configuraciones
            self._generate_configs(params, staging_dir)

            # Escribir command.txt
            net_dims_str = " ".join(map(str, params["net_dims"]))
            cmd_preview = (
                f"python run_sim.py --model {params['model']} --net_dims {net_dims_str} "
                f"--topology {params['topology']} --vcs {params['vcs']} --routing {params['routing']} "
                f"--batch_size {params['batch_size']} --input_len {params['input_len']} "
                f"--output_len {params['output_len']} --iter {params['iter']} "
                f"--tensor_degree {params['tensor_degree']} --skewness {params['skewness']} "
                f"--data_mode {params['data_mode']}"
            )
            with open(staging_dir / "command.txt", "w", encoding="utf-8") as cf:
                cf.write(cmd_preview + "\n")

            # 3. Preparar variables de entorno
            env = os.environ.copy()
            if params["debug_pids"]:
                env["SIM_DEBUG_PIDS"] = "1"
            else:
                env["SIM_DEBUG_PIDS"] = "0"

            # 4. Iniciar subproceso
            with self.lock:
                self.log_lines.append(f"🚀 Iniciando Co-Simulación en Staging: {folder_name}")
                self.log_lines.append(f"🖥️ Red: {dims_str} {params['topology'].upper()} | VCs: {params['vcs']} | Enrutamiento: {params['routing']}")
                self.log_lines.append(f"🧩 Paralelismo: Tensor Parallelism (TP) = {params['tensor_degree']} | Expert TP = 1")
                skew_desc = f"{params['skewness']} (Distribución Zipfiana)" if params['skewness'] > 0.0 else "0.0 (Uniforme)"
                self.log_lines.append(f"⚖️ Desbalanceo MoE: Skewness = {skew_desc}")
                self.log_lines.append(f"🧠 Concurrencia: Batch Size {params['batch_size']}")
                self.log_lines.append(f"🔄 Estadística: {params['iter']} Iteraciones x {params['output_len']} tokens")
                self.log_lines.append(f"📁 Directorio temporal: {staging_dir}")
                self.log_lines.append(f"⚙️ Comando CLI equivalente: {cmd_preview}")
                self.log_lines.append("-" * 65)

            log_file_path = staging_dir / "sim_output.txt"
            csv_file_path = staging_dir / "packet_tracking_debug.csv"
            csv_file = None
            if params["debug_pids"]:
                csv_file = open(csv_file_path, "w", encoding="utf-8")
                csv_file.write(
                    "PID,Source,Dest,Creation_Cycle,Inject_Cycle,Receive_Cycle,Total_Latency,"
                    "Network_Latency,Queueing_Delay,Num_Flits,Size_Bytes,Avg_Flit_Latency,"
                    "Throughput,Op_Type,Op_Idx,Op_Start_NS,Op_End_NS\n"
                )

            log_file = open(log_file_path, "w", encoding="utf-8")
            log_file.write(f"COMMAND EXECUTED: {cmd_preview}\n")
            log_file.write("-" * 65 + "\n")
            log_file.flush()

            process = subprocess.Popen(
                [str(executable)],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )

            with self.lock:
                self.current_process = process

            # Seguimiento de progreso
            total_iters = max(1, params["iter"])
            model_key = params["model"].lower()
            layers_per_iter = self.model_layers.get(model_key, 32)
            total_steps = total_iters * layers_per_iter
            current_iter = 0
            current_layer = 0

            # Expresiones regulares para monitorear progreso
            re_layer = re.compile(r"(?:MoE_decoder_|decoder_)(\d+)")
            re_cosim = re.compile(r"\[COSIM_ORACLE\]\s+(?:Scatter|Gather)\s+#(\d+)")
            re_iter_start = re.compile(r"-------------start-----------------")

            track_pids_count = 0

            for line in process.stdout:
                if self.aborted:
                    break

                # Interceptar trazas de paquetes
                if line.startswith("[TRACK_PID]"):
                    clean_row = line.strip().replace("[TRACK_PID] ", "").replace("[TRACK_PID]", "").strip()
                    if csv_file:
                        csv_file.write(clean_row + "\n")
                    track_pids_count += 1
                    continue

                # Escribir en log y buffer de memoria
                log_file.write(line)
                clean_line = line.rstrip("\r\n")

                with self.lock:
                    self.log_lines.append(clean_line)

                # Monitoreo de progreso
                if re_iter_start.search(clean_line):
                    current_iter = min(total_iters, current_iter + 1)

                m_layer = re_layer.search(clean_line)
                if m_layer:
                    current_layer = int(m_layer.group(1))

                m_cosim = re_cosim.search(clean_line)
                if m_cosim:
                    op_idx = int(m_cosim.group(1))
                    # Cada capa tiene Scatter y Gather
                    current_layer = max(current_layer, op_idx)

                # Calcular porcentaje aproximado
                eff_iter = max(1, current_iter)
                steps_done = (eff_iter - 1) * layers_per_iter + min(current_layer + 1, layers_per_iter)
                pct = min(98, max(5, int((steps_done / total_steps) * 100)))

                with self.lock:
                    self.progress_percent = pct
                    self.progress_detail = f"Iteración {eff_iter}/{total_iters} | Capa {current_layer + 1}/{layers_per_iter}"

            process.wait()

            if csv_file:
                csv_file.flush()
                csv_file.close()

            log_file.flush()
            log_file.close()

            # 5. Recoger archivos .trc de la base y moverlos a staging
            trc_count = 0
            search_dirs = [self.base_dir, self.build_dir]
            for sdir in search_dirs:
                if sdir.exists():
                    for f in os.listdir(sdir):
                        if f.startswith("TFM_device_") and f.endswith(".trc"):
                            src_path = sdir / f
                            dst_path = staging_dir / f
                            try:
                                shutil.move(str(src_path), str(dst_path))
                                trc_count += 1
                            except Exception:
                                pass

            with self.lock:
                if self.start_time:
                    self.elapsed_seconds = time.time() - self.start_time
                self.end_time = time.time()

                if self.aborted:
                    self.status = "aborted"
                    self.progress_detail = "Simulación abortada por el usuario."
                    self.log_lines.append("\n🛑 Simulación marcada como abortada.")
                elif process.returncode == 0:
                    self.status = "completed"
                    self.progress_percent = 100
                    self.progress_detail = "¡Simulación completada con éxito!"
                    self.log_lines.append("-" * 65)
                    self.log_lines.append(f"✅ Co-Simulación finalizada con éxito en {round(self.elapsed_seconds, 1)}s.")
                    self.log_lines.append(f"📦 Se recolectaron {trc_count} ficheros de traza TFM_device_*.trc.")
                    if params["debug_pids"]:
                        self.log_lines.append(f"🐛 Paquetes registrados en packet_tracking_debug.csv: {track_pids_count} filas.")
                    self.log_lines.append(f"💾 Resultados sellados en Staging: {staging_dir}")
                else:
                    self.status = "error"
                    self.error_message = f"El proceso ./build/run terminó con código de error {process.returncode}"
                    self.progress_detail = "Error en la ejecución de la simulación."
                    self.log_lines.append(f"\n❌ Error: {self.error_message}")

        except Exception as e:
            with self.lock:
                self.status = "error"
                self.error_message = str(e)
                self.progress_detail = f"Excepción interna: {e}"
                self.log_lines.append(f"\n💥 Excepción crítica en runner: {e}")
        finally:
            with self.lock:
                self.current_process = None


# Instancia única para el servidor
runner_instance = SimulationRunner()

