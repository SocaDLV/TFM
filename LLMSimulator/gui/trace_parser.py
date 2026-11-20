# -*- coding: utf-8 -*-
"""
Trace and Packet Tracking Parser for LLM-NoC Co-Simulation Workbench.
Reconstructs cycle-to-cycle GPU chronograms, packet flight data, macroscopic KPIs,
and synchronized hybrid split-screen projections directly from raw files
(.trc and packet_tracking_debug.csv) without generating static PNGs.
Supports multi-iteration analysis (Iteración 1..N o Simulación Completa).
"""

import os
import glob
import re
import json
import numpy as np
import pandas as pd
from pathlib import Path


def split_dataframe_by_drops(df, col_name, drop_threshold=-1.0):
    """
    Splits a DataFrame into sequential iteration segments whenever col_name drops
    by more than drop_threshold (e.g. START_NS < -1.0 or Op_Start_NS < -100.0).
    Returns a list of DataFrames: [seg_iter_1, seg_iter_2, ...].
    """
    if df.empty or col_name not in df.columns:
        return [df]
    drops = df[col_name].diff() < drop_threshold
    if not drops.any():
        return [df]
    cut_indices = [0] + list(df.index[drops]) + [len(df)]
    segments = []
    for i in range(len(cut_indices) - 1):
        seg = df.iloc[cut_indices[i] : cut_indices[i + 1]].copy().reset_index(drop=True)
        if not seg.empty:
            segments.append(seg)
    return segments if segments else [df]


def get_cluster_iteration_info(folder_path):
    """
    Scans all *device_*.trc files in folder_path to determine the number of iterations
    and the max wall-clock duration of each iteration across all GPUs.
    Returns: (num_iters, durations_list, offsets_list)
    """
    folder = Path(folder_path).resolve()
    trc_files = sorted(glob.glob(str(folder / "*device_*.trc")))
    if not trc_files:
        return 1, [0.0], [0.0]

    max_ends_per_iter = {}
    min_starts_per_iter = {}

    for tf in trc_files:
        try:
            df = pd.read_csv(tf, on_bad_lines="skip")
            df.columns = df.columns.str.strip()
            df["START_NS"] = pd.to_numeric(df["START_NS"], errors="coerce")
            df["END_NS"] = pd.to_numeric(df["END_NS"], errors="coerce")
            df["DURATION"] = pd.to_numeric(df["DURATION"], errors="coerce")
            df = df.dropna(subset=["START_NS", "END_NS", "DURATION"])
            df = df[df["DURATION"] > 0]
            if df.empty:
                continue

            segs = split_dataframe_by_drops(df, "START_NS", -1.0)
            for k, seg in enumerate(segs):
                s_min = float(seg["START_NS"].min())
                e_max = float(seg["END_NS"].max())
                min_starts_per_iter[k] = min(min_starts_per_iter.get(k, float("inf")), s_min)
                max_ends_per_iter[k] = max(max_ends_per_iter.get(k, 0.0), e_max)
        except Exception:
            pass

    num_iters = len(max_ends_per_iter) if max_ends_per_iter else 1
    durations = []
    for k in range(num_iters):
        s = min_starts_per_iter.get(k, 0.0)
        e = max_ends_per_iter.get(k, 1.0)
        durations.append(max(1.0, e - s))

    offsets = [0.0]
    for k in range(1, num_iters):
        offsets.append(offsets[-1] + durations[k - 1])

    return num_iters, durations, offsets


def load_network_ops_debug(folder_path, iteration="last", iteration_offsets=None):
    """
    Loads packet_tracking_debug.csv, segments by iteration, applies temporal offsets if iteration=='all',
    and aggregates statistics per network collective and per GPU.
    """
    csv_path = os.path.join(folder_path, "packet_tracking_debug.csv")
    if not os.path.exists(csv_path):
        return []

    try:
        df_p = pd.read_csv(csv_path, on_bad_lines="skip")
        if df_p.empty or "Op_Type" not in df_p.columns:
            return []

        df_p.columns = df_p.columns.str.strip()

        # Normalizar tipos
        for c in ["PID", "Source", "Dest", "Creation_Cycle", "Inject_Cycle", "Receive_Cycle",
                  "Total_Latency", "Num_Flits", "Op_Idx", "Op_Start_NS", "Op_End_NS", "Avg_Flit_Latency", "Throughput"]:
            if c in df_p.columns:
                df_p[c] = pd.to_numeric(df_p[c], errors="coerce")

        segs = split_dataframe_by_drops(df_p, "Op_Start_NS", -100.0)
        num_iters = len(segs)

        if iteration == "all":
            processed_segs = []
            for k, seg in enumerate(segs):
                off = iteration_offsets[k] if (iteration_offsets and k < len(iteration_offsets)) else 0.0
                seg = seg.copy()
                if off > 0:
                    if "Op_Start_NS" in seg.columns:
                        seg["Op_Start_NS"] = seg["Op_Start_NS"] + off
                    if "Op_End_NS" in seg.columns:
                        seg["Op_End_NS"] = seg["Op_End_NS"] + off
                seg["ITERATION"] = k + 1
                processed_segs.append(seg)
            df_active = pd.concat(processed_segs, ignore_index=True)
        elif iteration == "last":
            df_active = segs[-1].copy()
            df_active["ITERATION"] = num_iters
        else:
            try:
                iter_k = int(iteration) - 1
                if 0 <= iter_k < num_iters:
                    df_active = segs[iter_k].copy()
                    df_active["ITERATION"] = iter_k + 1
                else:
                    df_active = segs[-1].copy()
                    df_active["ITERATION"] = num_iters
            except ValueError:
                df_active = segs[-1].copy()
                df_active["ITERATION"] = num_iters

        all_nodes = set()
        if "Source" in df_active.columns:
            all_nodes.update(df_active["Source"].dropna().unique())
        if "Dest" in df_active.columns:
            all_nodes.update(df_active["Dest"].dropna().unique())
        max_node = int(max(all_nodes)) if all_nodes else 7
        num_gpus = max(8, max_node + 1)

        ops = []
        group_cols = ["ITERATION", "Op_Type", "Op_Idx"] if "ITERATION" in df_active.columns else ["Op_Type", "Op_Idx"]
        for keys, grp in df_active.groupby(group_cols, sort=False):
            if "ITERATION" in df_active.columns:
                iter_num, op_type, op_idx = keys
            else:
                op_type, op_idx = keys
                iter_num = 1

            start_ns = float(grp["Op_Start_NS"].iloc[0]) if "Op_Start_NS" in grp.columns else 0.0
            end_ns = float(grp["Op_End_NS"].iloc[0]) if "Op_End_NS" in grp.columns else 0.0
            min_pid = int(grp["PID"].min())
            max_pid = int(grp["PID"].max())
            total_pkts = len(grp)
            final_avg_lat = float(grp["Avg_Flit_Latency"].iloc[-1]) if "Avg_Flit_Latency" in grp.columns else 0.0
            final_prod = float(grp["Throughput"].iloc[-1]) if "Throughput" in grp.columns else 0.0

            op_type_lower = str(op_type).lower()
            gpu_data = {}
            for d in range(num_gpus):
                if "scatter" in op_type_lower:
                    sub = grp[grp["Dest"] == d]
                    role = "RX (Experto Destino)"
                elif "gather" in op_type_lower:
                    sub = grp[grp["Source"] == d]
                    role = "TX (Activación Origen)"
                elif "allreduce" in op_type_lower or "all_reduce" in op_type_lower:
                    sub = grp[grp["Dest"] == d]
                    if sub.empty:
                        sub = grp[grp["Source"] == d]
                    role = "Ring TP"
                else:
                    sub = grp[(grp["Dest"] == d) | (grp["Source"] == d)]
                    role = "P2P"

                n_local = len(sub)
                if n_local > 0:
                    lat_local = float(sub["Total_Latency"].mean()) if "Total_Latency" in sub.columns else 0.0
                    flits_local = int(sub["Num_Flits"].sum()) if "Num_Flits" in sub.columns else n_local * 9
                    min_pid_local = int(sub["PID"].min())
                    max_pid_local = int(sub["PID"].max())
                else:
                    lat_local = 0.0
                    flits_local = 0
                    min_pid_local = 0
                    max_pid_local = 0

                gpu_data[d] = {
                    "pkts": n_local,
                    "lat": round(lat_local, 1),
                    "flits": flits_local,
                    "min_pid": min_pid_local,
                    "max_pid": max_pid_local,
                    "role": role
                }

            ops.append({
                "iter": int(iter_num),
                "type": str(op_type),
                "idx": int(op_idx) if str(op_idx).isdigit() else 1,
                "start_ns": start_ns,
                "end_ns": end_ns,
                "min_pid": min_pid,
                "max_pid": max_pid,
                "total_pkts": total_pkts,
                "avg_flit_lat": round(final_avg_lat, 2),
                "throughput": round(final_prod, 2),
                "gpu_data": gpu_data
            })
        return ops
    except Exception as e:
        print(f"⚠️ trace_parser: Error al parsear packet_tracking_debug.csv: {e}")
        return []


def match_network_op(label, start_ns, end_ns, ops):
    """Finds the corresponding network collective in ops list."""
    if not ops:
        return None
    for op in ops:
        if op["type"].lower() in label.lower() or label.lower() in op["type"].lower():
            if (start_ns < op["end_ns"] + 150.0 and end_ns > op["start_ns"] - 150.0):
                return op
    return None


def get_simulation_summary(folder_path, iteration="last"):
    """
    Computes macroscopic KPIs and architecture metadata for a simulation folder,
    supporting specific iterations ('1', '2'...), the steady-state ('last'), or full run ('all').
    """
    folder = Path(folder_path).resolve()
    if not folder.exists():
        raise FileNotFoundError(f"Carpeta no encontrada: {folder_path}")

    # 1. Metadatos de config.yaml, test.cfg, .trc y gui_metadata.json
    fname = folder.name.lower()
    default_model = "mixtral"
    if "deepseek" in fname:
        default_model = "deepseekV3"
    elif "llama" in fname:
        default_model = "llama"

    default_topo = "torus"
    if "mesh" in fname:
        default_topo = "mesh"

    # Conteo real de dispositivos a partir de archivos .trc locales
    local_trc = sorted(glob.glob(str(folder / "*device_*.trc")))
    gpu_count = len(local_trc) if local_trc else 8

    # Heurística de dimensiones de red
    net_dims = str(gpu_count)
    m_dim = re.search(r"(\d+)x(\d+)dev", folder.name)
    if m_dim:
        net_dims = f"{m_dim.group(1)} {m_dim.group(2)}"
        default_topo = "mesh"
    elif re.search(r"(\d+)dev", folder.name):
        net_dims = re.search(r"(\d+)dev", folder.name).group(1)

    metadata = {
        "folder_name": folder.name,
        "model": default_model,
        "topology": default_topo,
        "net_dims": net_dims,
        "num_gpus": gpu_count,
        "vcs": 4,
        "routing": "dim_order",
        "batch_size": 32,
        "input_len": 1024,
        "output_len": 2,
        "iter": 2,
        "tensor_degree": 1,
        "skewness": 0.0,
        "gpu_gen": "B100",
        "data_mode": "synthesis",
        "label": "",
        "saved_at": None
    }

    gui_meta_path = folder / "gui_metadata.json"
    if gui_meta_path.exists():
        try:
            with open(gui_meta_path, "r", encoding="utf-8") as f:
                saved_meta = json.load(f)
                metadata.update(saved_meta)
        except Exception:
            pass

    cfg_yaml = folder / "config.yaml"
    if cfg_yaml.exists():
        try:
            with open(cfg_yaml, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("model_name:"):
                        metadata["model"] = line.split(":", 1)[1].strip()
                    elif line.startswith("gpu_gen:"):
                        metadata["gpu_gen"] = line.split(":", 1)[1].strip()
                    elif line.startswith("num_device:"):
                        metadata["num_gpus"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("none_expert_tensor_degree:"):
                        metadata["tensor_degree"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("max_batch_size:"):
                        metadata["batch_size"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("input_len:"):
                        metadata["input_len"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("output_len:"):
                        metadata["output_len"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("iter:"):
                        metadata["iter"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("skewness:"):
                        metadata["skewness"] = float(line.split(":", 1)[1].strip())
                    elif line.startswith("data:"):
                        metadata["data_mode"] = line.split(":", 1)[1].strip()
        except Exception:
            pass

    test_cfg = folder / "test.cfg"
    if test_cfg.exists():
        try:
            k_val = None
            n_val = None
            net_file = ""
            with open(test_cfg, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("topology"):
                        raw_topo = line.split("=")[1].replace(";", "").strip().lower()
                        if raw_topo in ["mesh", "torus", "ring"]:
                            metadata["topology"] = raw_topo
                        elif raw_topo == "anynet":
                            metadata["topology"] = "mesh"  # Default anynet to mesh if custom
                    elif line.startswith("network_file"):
                        net_file = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("routing_function"):
                        metadata["routing"] = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("num_vcs"):
                        metadata["vcs"] = int(line.split("=")[1].replace(";", "").strip())
                    elif line.startswith("k =") or line.startswith("k="):
                        k_val = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("n =") or line.startswith("n="):
                        n_val = line.split("=")[1].replace(";", "").strip()

            if "mesh_4x2" in net_file or "4x2" in folder.name:
                metadata["topology"] = "mesh"
                metadata["net_dims"] = "4 2"
            elif k_val and n_val and k_val == "2" and n_val == "2":
                metadata["topology"] = "mesh"
                metadata["net_dims"] = "2 2"
            elif k_val and n_val and k_val == "4" and n_val == "4":
                metadata["topology"] = "mesh"
                metadata["net_dims"] = "4 4"
        except Exception:
            pass

    # Asegurar num_gpus = len(local_trc) si existen archivos .trc
    if local_trc:
        metadata["num_gpus"] = len(local_trc)

    # 2. Análisis multi-iteración de los archivos .trc
    num_iters, durations, offsets = get_cluster_iteration_info(folder)
    metadata["num_iterations"] = num_iters

    # Resolver índice de iteración objetivo
    if iteration == "all":
        target_iter_mode = "all"
    elif iteration == "last":
        target_iter_mode = num_iters - 1
    else:
        try:
            val = int(iteration) - 1
            target_iter_mode = max(0, min(val, num_iters - 1))
        except ValueError:
            target_iter_mode = num_iters - 1

    trc_files = glob.glob(str(folder / "*device_*.trc"))
    compute_total = 0.0
    transit_total = 0.0
    stall_total = 0.0
    scatter_total = 0.0
    gather_total = 0.0
    allreduce_total = 0.0
    devices_counted = 0

    for trc_path in sorted(trc_files):
        try:
            df = pd.read_csv(trc_path, on_bad_lines="skip")
            df.columns = df.columns.str.strip()
            df["START_NS"] = pd.to_numeric(df["START_NS"], errors="coerce")
            df["END_NS"] = pd.to_numeric(df["END_NS"], errors="coerce")
            df["DURATION"] = pd.to_numeric(df["DURATION"], errors="coerce")
            df = df.dropna(subset=["START_NS", "END_NS", "DURATION"])
            df = df[df["DURATION"] > 0]
            if df.empty:
                continue

            segs = split_dataframe_by_drops(df, "START_NS", -1.0)
            if target_iter_mode == "all":
                df_active = pd.concat(segs, ignore_index=True)
            else:
                idx = min(target_iter_mode, len(segs) - 1)
                df_active = segs[idx]

            df_active["TYPE"] = df_active["TYPE"].astype(str).str.strip().str.lower()
            scatter = df_active[df_active["TYPE"].str.contains("scatter")]["DURATION"].sum()
            gather = df_active[df_active["TYPE"].str.contains("gather")]["DURATION"].sum()
            all_red = df_active[df_active["TYPE"].str.contains("all_reduce|allreduce")]["DURATION"].sum()
            transit = scatter + gather + all_red

            stall = df_active[df_active["TYPE"].str.contains("stall")]["DURATION"].sum()
            non_comp_mask = df_active["TYPE"].str.contains("scatter|gather|stall|all_reduce|allreduce")
            compute = df_active[~non_comp_mask]["DURATION"].sum()

            compute_total += compute
            transit_total += transit
            stall_total += stall
            scatter_total += scatter
            gather_total += gather
            allreduce_total += all_red
            devices_counted += 1
        except Exception as e:
            print(f"⚠️ trace_parser: Error en {trc_path}: {e}")

    num_gpus = max(devices_counted, metadata["num_gpus"])
    if target_iter_mode == "all":
        cluster_wall_clock_ns = float(sum(durations))
    else:
        cluster_wall_clock_ns = float(durations[target_iter_mode])

    c_avg_ns = compute_total / devices_counted if devices_counted > 0 else 0.0
    t_avg_ns = transit_total / devices_counted if devices_counted > 0 else 0.0
    s_avg_ns = stall_total / devices_counted if devices_counted > 0 else 0.0
    scat_avg_ns = scatter_total / devices_counted if devices_counted > 0 else 0.0
    gath_avg_ns = gather_total / devices_counted if devices_counted > 0 else 0.0
    ar_avg_ns = allreduce_total / devices_counted if devices_counted > 0 else 0.0

    # 3. Métricas de packet_tracking_debug.csv para el ámbito seleccionado
    csv_path = folder / "packet_tracking_debug.csv"
    has_packet_csv = csv_path.exists()
    total_packets = 0
    total_flits = 0
    lambda_rate = 0.0
    avg_flit_lat = 0.0
    avg_pkt_lat = 0.0
    avg_queue_delay = 0.0

    if has_packet_csv:
        try:
            df_p = pd.read_csv(csv_path, on_bad_lines="skip")
            if not df_p.empty and "Creation_Cycle" in df_p.columns:
                df_p.columns = df_p.columns.str.strip()
                for c in ["Creation_Cycle", "Receive_Cycle", "Num_Flits", "Avg_Flit_Latency", "Total_Latency", "Queueing_Delay", "Op_Start_NS"]:
                    if c in df_p.columns:
                        df_p[c] = pd.to_numeric(df_p[c], errors="coerce")

                segs_csv = split_dataframe_by_drops(df_p, "Op_Start_NS", -100.0)
                if target_iter_mode == "all":
                    df_slice = pd.concat(segs_csv, ignore_index=True)
                else:
                    c_idx = min(target_iter_mode, len(segs_csv) - 1)
                    df_slice = segs_csv[c_idx]

                df_slice = df_slice.dropna(subset=["Creation_Cycle", "Receive_Cycle"])
                total_packets = len(df_slice)
                if "Num_Flits" in df_slice.columns:
                    total_flits = int(df_slice["Num_Flits"].sum())
                else:
                    total_flits = total_packets * 9

                if total_packets > 0:
                    if "Total_Latency" not in df_slice.columns and "Latency" in df_slice.columns:
                        df_slice["Total_Latency"] = df_slice["Latency"]
                    if "Avg_Flit_Latency" not in df_slice.columns:
                        df_slice["Avg_Flit_Latency"] = df_slice["Total_Latency"]
                    if "Num_Flits" not in df_slice.columns:
                        df_slice["Num_Flits"] = 9

                    op_points = []
                    if "Op_Type" in df_slice.columns and "Op_Idx" in df_slice.columns:
                        for (op_t, op_i), grp in df_slice.groupby(["Op_Type", "Op_Idx"]):
                            f_cnt = grp["Num_Flits"].sum()
                            dur = max(1.0, float(grp["Receive_Cycle"].max() - grp["Creation_Cycle"].min()))
                            l_flits = f_cnt / (num_gpus * dur)
                            op_points.append(l_flits)
                    else:
                        f_cnt = df_slice["Num_Flits"].sum()
                        dur = max(1.0, float(df_slice["Receive_Cycle"].max() - df_slice["Creation_Cycle"].min()))
                        op_points.append(f_cnt / (num_gpus * dur))

                    if op_points:
                        lambda_rate = float(np.mean(op_points))
                    else:
                        dur_cycles = max(1.0, cluster_wall_clock_ns)
                        lambda_rate = total_flits / (num_gpus * dur_cycles)

                    if "Avg_Flit_Latency" in df_slice.columns:
                        avg_flit_lat = float(df_slice["Avg_Flit_Latency"].mean())
                    if "Total_Latency" in df_slice.columns:
                        avg_pkt_lat = float(df_slice["Total_Latency"].mean())
                    if "Queueing_Delay" in df_slice.columns:
                        avg_queue_delay = float(df_slice["Queueing_Delay"].mean())
        except Exception as e:
            print(f"⚠️ trace_parser: Error leyendo CSV en summary: {e}")

    # Ratios porcentuales
    tot_ref = float(cluster_wall_clock_ns) if cluster_wall_clock_ns > 0 else float(c_avg_ns + t_avg_ns + s_avg_ns)
    c_pct = (float(c_avg_ns) / tot_ref * 100.0) if tot_ref > 0 else 0.0
    t_pct = (float(t_avg_ns) / tot_ref * 100.0) if tot_ref > 0 else 0.0
    s_pct = (float(s_avg_ns) / tot_ref * 100.0) if tot_ref > 0 else 0.0

    kpis_data = {
        "num_iterations": int(num_iters),
        "active_iteration": str(iteration),
        "wall_clock_ns": round(float(cluster_wall_clock_ns), 1),
        "wall_clock_us": round(float(cluster_wall_clock_ns) / 1000.0, 2),
        "compute_time_ns": round(float(c_avg_ns), 1),
        "compute_ns": round(float(c_avg_ns), 1),
        "compute_us": round(float(c_avg_ns) / 1000.0, 2),
        "compute_pct": round(float(c_pct), 1),
        "network_time_ns": round(float(t_avg_ns), 1),
        "transit_ns": round(float(t_avg_ns), 1),
        "transit_us": round(float(t_avg_ns) / 1000.0, 2),
        "network_pct": round(float(t_pct), 1),
        "transit_pct": round(float(t_pct), 1),
        "stall_time_ns": round(float(s_avg_ns), 1),
        "stall_ns": round(float(s_avg_ns), 1),
        "stall_us": round(float(s_avg_ns) / 1000.0, 2),
        "stall_pct": round(float(s_pct), 1),
        "scatter_ns": round(float(scat_avg_ns), 1),
        "moe_scatter_ns": round(float(scat_avg_ns), 1),
        "scatter_us": round(float(scat_avg_ns) / 1000.0, 2),
        "gather_ns": round(float(gath_avg_ns), 1),
        "moe_gather_ns": round(float(gath_avg_ns), 1),
        "gather_us": round(float(gath_avg_ns) / 1000.0, 2),
        "allreduce_ns": round(float(ar_avg_ns), 1),
        "all_reduce_ns": round(float(ar_avg_ns), 1),
        "allreduce_us": round(float(ar_avg_ns) / 1000.0, 2),
        "real_injection_rate_lambda": round(float(lambda_rate), 4),
        "lambda_rate": round(float(lambda_rate), 4),
        "avg_flit_lat_cycles": round(float(avg_flit_lat), 1),
        "avg_flit_latency": round(float(avg_flit_lat), 1),
        "avg_pkt_lat_cycles": round(float(avg_pkt_lat), 1),
        "avg_packet_latency": round(float(avg_pkt_lat), 1),
        "avg_queueing_delay": round(float(avg_queue_delay), 1),
        "total_packets": int(total_packets),
        "total_flits": int(total_flits),
        "has_packet_csv": bool(has_packet_csv),
        "devices_counted": int(devices_counted)
    }

    return {
        "metadata": metadata,
        "kpis": kpis_data,
        **metadata,
        **kpis_data
    }


def parse_single_trc_segment(df, gpu_id, offset_ns=0.0, iter_num=1):
    """
    Parses a single contiguous DataFrame segment (one iteration) of a .trc file.
    Applies offset_ns to all absolute timestamps (start_ns, end_ns, sub_ops).
    """
    df = df[df["DURATION"] > 0].reset_index(drop=True)
    if df.empty:
        return []

    # 1. Extracción de capa
    explicit_layer = df["DETAILS"].str.extract(r"(?:MoE_decoder_|decoder_)(\d+)")[0]
    df["EXPLICIT_LAYER"] = pd.to_numeric(explicit_layer, errors="coerce")
    layers = [None] * len(df)
    for i in range(len(df)):
        if pd.notna(df.at[i, "EXPLICIT_LAYER"]):
            layers[i] = int(df.at[i, "EXPLICIT_LAYER"])
        elif "input_layer_norm" in df.at[i, "TYPE"].lower():
            for j in range(i + 1, min(i + 5, len(df))):
                if pd.notna(df.at[j, "EXPLICIT_LAYER"]):
                    layers[i] = int(df.at[j, "EXPLICIT_LAYER"])
                    break
    df["LAYER"] = pd.Series(layers).ffill().bfill().fillna(0).astype(int)

    # 2. Métricas Comp_ns y Mem_ns
    comp_ns = df["DETAILS"].str.extract(r"Comp_ns:([0-9.]+)")[0]
    mem_ns = df["DETAILS"].str.extract(r"Mem_ns:([0-9.]+)")[0]
    df["COMP_NS"] = pd.to_numeric(comp_ns, errors="coerce").fillna(0.0)
    df["MEM_NS"] = pd.to_numeric(mem_ns, errors="coerce").fillna(0.0)

    # 3. Clasificación semántica
    def classify_row(row):
        t = row["TYPE"].lower()
        d = row["DETAILS"].lower()
        op = t + " " + d

        if "all_reduce" in op or "allreduce" in op:
            return "all_reduce", "#8e44ad", "AllReduce", "AllReduce", None
        elif "scatter" in op:
            return "scatter", "#3498db", "Scatter", "Scatter", None
        elif "gather" in op:
            return "gather", "#3498db", "Gather", "Gather", None
        elif "stall" in op:
            return "stall", "#e74c3c", "Stall", "Stall", None

        if "shared_expert" in op:
            shared_m = re.search(r"shared_expert_ffn_(\d+)", op)
            shared_id = int(shared_m.group(1)) if shared_m else 0
            if "gate_proj" in op:
                micro = "Gate_Proj"
            elif "activation" in op or "act" in op or "silu" in op:
                micro = "SiLU"
            elif "up_proj" in op:
                micro = "Up_Proj"
            elif "down_proj" in op:
                micro = "Down_Proj"
            else:
                micro = "FFN"
            return "calc", "#2ecc71", "SharedExpert", micro, shared_id

        exp_m = re.search(r"expert_ffn_(\d+)", op)
        if "expert_ffn" in op or exp_m:
            exp_id = int(exp_m.group(1)) if exp_m else None
            if "gate_proj" in op:
                micro = "Gate_Proj"
            elif "activation" in op or "act" in op or "silu" in op:
                micro = "SiLU"
            elif "up_proj" in op:
                micro = "Up_Proj"
            elif "down_proj" in op:
                micro = "Down_Proj"
            else:
                micro = "FFN"
            return "calc", "#2ecc71", "ExpertFFN", micro, exp_id

        if "feedforward" in op:
            if "gate_proj" in op:
                micro = "Gate_Proj"
            elif "activation" in op or "act" in op or "silu" in op:
                micro = "SiLU"
            elif "up_proj" in op:
                micro = "Up_Proj"
            elif "down_proj" in op:
                micro = "Down_Proj"
            else:
                micro = "FFN"
            return "calc", "#2ecc71", "DenseFFN", micro, None

        if "attn_qkv" in op:
            return "calc", "#2ecc71", "Attention", "QKV_Proj", None
        elif "attentiongen" in op or "self_attention" in op:
            return "calc", "#2ecc71", "Attention", "AttnGen", None
        elif "attn_o_proj" in op or "attn_o_up_proj" in op:
            return "calc", "#2ecc71", "Attention", "O_Proj", None
        elif "input_layer_norm" in op or "post_attn_layer_norm" in op:
            return "calc", "#2ecc71", "Attention", "LN", None
        elif "residual_1" in op:
            return "calc", "#2ecc71", "Attention", "Res1", None
        elif "gate_fn" in op:
            return "calc", "#2ecc71", "Attention", "Gate", None
        elif "residual_2" in op:
            return "calc", "#2ecc71", "Residual", "Res2", None
        elif "attn" in op or "attention" in op or "rope" in op or "latent" in op:
            micro = "MLA_Proj"
            if "mla" in op:
                micro = "MLA_Gen"
            elif "rope" in op:
                micro = "RoPE"
            elif "proj" in op:
                micro = "Proj"
            return "calc", "#2ecc71", "Attention", micro, None
        else:
            sub = "Linear" if "pop_operation" in op else row["TYPE"][:10]
            return "calc", "#2ecc71", sub, sub, None

    parsed = df.apply(classify_row, axis=1)
    df["CATEGORY"] = [p[0] for p in parsed]
    df["COLOR"] = [p[1] for p in parsed]
    df["MACRO_OP"] = [p[2] for p in parsed]
    df["MICRO_OP"] = [p[3] for p in parsed]
    df["EXP_ID"] = [p[4] for p in parsed]

    # 4. Agrupación contigua por Capa y Macro-Operación
    df["group"] = (
        (df["LAYER"] != df["LAYER"].shift(1))
        | (df["CATEGORY"] != df["CATEGORY"].shift(1))
        | (df["MACRO_OP"] != df["MACRO_OP"].shift(1))
    ).cumsum()

    blocks = []
    for _, grp in df.groupby("group", sort=False):
        first_row = grp.iloc[0]
        start_ns = float(grp["START_NS"].min()) + offset_ns
        end_ns = float(grp["END_NS"].max()) + offset_ns
        dur_ns = end_ns - start_ns
        category = first_row["CATEGORY"]
        color = first_row["COLOR"]
        macro_op = first_row["MACRO_OP"]
        layer = int(first_row["LAYER"])

        # Fronteras internas y desglose de micro-operaciones
        sub_ops = []
        for _, r in grp.iterrows():
            r_dur = float(r["DURATION"])
            if r_dur > 0.0:
                c_ns = float(r["COMP_NS"]) if "COMP_NS" in r else 0.0
                m_ns = float(r["MEM_NS"]) if "MEM_NS" in r else 0.0
                if (c_ns + m_ns) > 0.0:
                    s_mem = round(min(100.0, max(0.0, (m_ns / (c_ns + m_ns)) * 100.0)), 1)
                else:
                    s_mem = 0.0

                sub_ops.append({
                    "start_ns": float(r["START_NS"]) + offset_ns,
                    "end_ns": float(r["END_NS"]) + offset_ns,
                    "duration_ns": r_dur,
                    "name": str(r["MICRO_OP"]),
                    "comp_ns": c_ns,
                    "mem_ns": m_ns,
                    "mem_pct": s_mem,
                    "mem_bound_pct": s_mem
                })

        # Secuencia descriptiva
        if macro_op == "Attention":
            if any("mla" in str(u).lower() or "rope" in str(u).lower() for u in grp["MICRO_OP"]):
                seq_str = "(LN + MLA_Compress + RoPE + Absorb_Gen + Up_Proj + O_Proj + Res)"
            else:
                seq_str = "(LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)"
        elif macro_op == "DenseFFN":
            seq_str = "(DenseFFN: Gate_Proj + SiLU + Up_Proj + Down_Proj)"
        elif macro_op == "SharedExpert":
            seq_str = "(SharedExp#0: Gate_Proj + SiLU + Up_Proj + Down_Proj)"
        elif macro_op == "ExpertFFN":
            exp_ids = sorted(list(set(int(e) for e in grp["EXP_ID"].dropna().unique())))
            if len(exp_ids) == 1:
                seq_str = f"(Exp#{exp_ids[0]}: Gate_Proj + SiLU + Up_Proj + Down_Proj)"
            elif len(exp_ids) > 1:
                if len(exp_ids) <= 3:
                    ids_str = ",".join(str(e) for e in exp_ids)
                    seq_str = f"(Exp#{ids_str}: {len(exp_ids)}x[Gate+SiLU+Up+Down])"
                else:
                    seq_str = f"(Exp#{exp_ids[0]}..#{exp_ids[-1]}: {len(exp_ids)}x[Gate+SiLU+Up+Down])"
            else:
                seq_str = "(ExpertFFN: Gate + SiLU + Up + Down)"
        elif category in ["scatter", "gather", "all_reduce", "stall"]:
            seq_str = ""
        else:
            unique_micros = []
            for u in grp["MICRO_OP"].unique():
                if u not in unique_micros:
                    unique_micros.append(str(u))
            seq_str = f"({' + '.join(unique_micros)})"

        tot_comp = float(grp["COMP_NS"].sum())
        tot_mem = float(grp["MEM_NS"].sum())
        mem_bound_pct = None
        if (tot_comp + tot_mem) > 0.0:
            mem_bound_pct = round(min(100.0, max(0.0, (tot_mem / (tot_comp + tot_mem)) * 100.0)), 1)

        title = f"Layer {layer} | {macro_op}"
        if category == "stall":
            title = f"Layer {layer} | Stall"
        elif category == "all_reduce":
            title = f"Layer {layer} | AllReduce"

        blocks.append({
            "iter": int(iter_num),
            "gpu_id": gpu_id,
            "layer": layer,
            "category": category,
            "color": color,
            "macro_op": macro_op,
            "title": title,
            "subtitle": seq_str,
            "start_ns": round(start_ns, 1),
            "end_ns": round(end_ns, 1),
            "duration_ns": round(dur_ns, 1),
            "mem_bound_pct": mem_bound_pct,
            "mem_pct": mem_bound_pct,
            "comp_ns": tot_comp,
            "mem_ns": tot_mem,
            "sub_ops": sub_ops,
            "local_net": None
        })

    return blocks


def parse_single_trc(filepath, iteration="last", iteration_offsets=None):
    """
    Parses a single .trc file. Depending on iteration, extracts either a single iteration
    ('last' or '1'..'N') or concatenates all iterations with offsets ('all').
    """
    basename = os.path.basename(filepath)
    try:
        gpu_id = int(basename.split("_")[-1].split(".")[0])
    except Exception:
        gpu_id = 0

    df = pd.read_csv(filepath, on_bad_lines="skip")
    df.columns = df.columns.str.strip()
    df["GPU"] = gpu_id
    df["START_NS"] = pd.to_numeric(df["START_NS"], errors="coerce")
    df["END_NS"] = pd.to_numeric(df["END_NS"], errors="coerce")
    df["DURATION"] = pd.to_numeric(df["DURATION"], errors="coerce")
    df["TYPE"] = df["TYPE"].astype(str).str.strip()
    df["DETAILS"] = df["DETAILS"].fillna("").astype(str).str.strip()
    df = df.dropna(subset=["START_NS", "END_NS", "DURATION"])

    segs = split_dataframe_by_drops(df, "START_NS", -1.0)
    num_iters = len(segs)

    if iteration == "all":
        all_blocks = []
        for k, seg in enumerate(segs):
            off = iteration_offsets[k] if (iteration_offsets and k < len(iteration_offsets)) else 0.0
            blocks_k = parse_single_trc_segment(seg, gpu_id, offset_ns=off, iter_num=k + 1)
            all_blocks.extend(blocks_k)
        return all_blocks
    elif iteration == "last":
        return parse_single_trc_segment(segs[-1], gpu_id, offset_ns=0.0, iter_num=num_iters)
    else:
        try:
            val = int(iteration) - 1
            idx = max(0, min(val, num_iters - 1))
        except ValueError:
            idx = num_iters - 1
        return parse_single_trc_segment(segs[idx], gpu_id, offset_ns=0.0, iter_num=idx + 1)


def get_chronogram_data(folder_path, iteration="last"):
    """
    Parses all .trc files in folder, applies network ops matching per GPU,
    and returns a consolidated timeline for HTML5 Canvas rendering.
    Supports iteration='last', 'all', or '1'..'N'.
    """
    folder = Path(folder_path).resolve()
    trc_files = glob.glob(str(folder / "*device_*.trc"))
    if not trc_files:
        raise FileNotFoundError(f"No se encontraron ficheros *device_*.trc en: {folder_path}")

    num_iters, durations, offsets = get_cluster_iteration_info(folder)
    network_ops = load_network_ops_debug(folder_path, iteration=iteration, iteration_offsets=offsets)

    all_blocks = []
    for tf in sorted(trc_files):
        blocks = parse_single_trc(tf, iteration=iteration, iteration_offsets=offsets)
        all_blocks.extend(blocks)

    if not all_blocks:
        return {
            "num_gpus": 0,
            "num_iterations": num_iters,
            "active_iteration": str(iteration),
            "iteration_markers": [],
            "min_ns": 0,
            "max_ns": 0,
            "tracks": [],
            "blocks": []
        }

    num_gpus = max(b["gpu_id"] for b in all_blocks) + 1
    min_ns = min(b["start_ns"] for b in all_blocks)
    max_ns = max(b["end_ns"] for b in all_blocks)

    # Enriquecer bloques de red con datos locales de GPU
    for b in all_blocks:
        if b["category"] in ["scatter", "gather", "all_reduce"]:
            matched_op = match_network_op(b["macro_op"], b["start_ns"], b["end_ns"], network_ops)
            if matched_op:
                gpu_id = b["gpu_id"]
                loc = matched_op["gpu_data"].get(gpu_id, {})
                pkts = loc.get("pkts", 0)
                lat = loc.get("lat", 0.0)
                flits = loc.get("flits", 0)
                if pkts > 0 and flits == 0:
                    flits = pkts * 9
                    loc["flits"] = flits
                dur_ns = max(1.0, b["duration_ns"])
                prod = round(flits / dur_ns, 2)
                role = loc.get("role", "Red")

                b["local_net"] = {
                    "op_type": matched_op["type"],
                    "op_idx": matched_op["idx"],
                    "pkts": pkts,
                    "flits": flits,
                    "avg_lat_cycles": lat,
                    "prod_flits_cycle": prod,
                    "total_pkts_collective": matched_op["total_pkts"],
                    "global_avg_flit_lat": matched_op["avg_flit_lat"],
                    "role": role
                }
                b["title"] = f"Layer {b['layer']} | {matched_op['type']} Nº{matched_op['idx']}"
                b["subtitle"] = f"{pkts} pkts | Lat.Media: {lat}c | Prod: {prod} f/c"

    # Ordenar bloques cronológicamente
    all_blocks.sort(key=lambda x: (x["gpu_id"], x["start_ns"]))

    # Organizar tracks individuales por GPU
    tracks = [[] for _ in range(num_gpus)]
    for b in all_blocks:
        b["block_type"] = b["category"]
        if b.get("local_net"):
            b["local_packets"] = b["local_net"].get("pkts", 0)
            b["local_flits"] = b["local_net"].get("flits", 0)
            b["avg_lat_cycles"] = b["local_net"].get("avg_lat_cycles", 0.0)
            b["throughput_flits_per_cycle"] = b["local_net"].get("prod_flits_cycle", 0.0)
        tracks[b["gpu_id"]].append(b)

    # Iteration markers para líneas divisorias en el Canvas
    if iteration == "all":
        iteration_markers = [
            {"iter": k + 1, "start_ns": round(offsets[k], 1), "duration_ns": round(durations[k], 1)}
            for k in range(num_iters)
        ]
    else:
        iter_num = num_iters if iteration == "last" else int(iteration)
        iteration_markers = [
            {"iter": iter_num, "start_ns": 0.0, "duration_ns": round(max_ns - min_ns, 1)}
        ]

    return {
        "num_gpus": num_gpus,
        "num_iterations": num_iters,
        "active_iteration": str(iteration),
        "iteration_markers": iteration_markers,
        "min_ns": round(min_ns, 1),
        "max_ns": round(max_ns, 1),
        "min_time_ns": round(min_ns, 1),
        "max_time_ns": round(max_ns, 1),
        "total_span_ns": round(max_ns - min_ns, 1),
        "total_duration_us": round((max_ns - min_ns) / 1000.0, 2),
        "total_blocks": len(all_blocks),
        "tracks": tracks,
        "blocks": all_blocks
    }


def get_packet_tracking_data(folder_path, offset=0, limit=150, regime="custom", iteration="last"):
    """
    Reads packet_tracking_debug.csv, filters according to iteration,
    and returns a paginated slice supporting regime presets ('free', 'medium', 'critical', 'custom').
    """
    folder = Path(folder_path).resolve()
    csv_path = folder / "packet_tracking_debug.csv"
    if not csv_path.exists():
        return {
            "has_data": False,
            "num_iterations": 1,
            "active_iteration": str(iteration),
            "total_packets": 0,
            "offset": 0,
            "limit": limit,
            "regime": regime,
            "packets": []
        }

    df = pd.read_csv(csv_path, on_bad_lines="skip")
    if df.empty or "Creation_Cycle" not in df.columns:
        return {
            "has_data": False,
            "num_iterations": 1,
            "active_iteration": str(iteration),
            "total_packets": 0,
            "offset": 0,
            "limit": limit,
            "regime": regime,
            "packets": []
        }

    df.columns = df.columns.str.strip()

    for col in ["PID", "Source", "Dest", "Creation_Cycle", "Inject_Cycle", "Receive_Cycle",
                "Total_Latency", "Network_Latency", "Queueing_Delay", "Num_Flits", "Size_Bytes",
                "Avg_Flit_Latency", "Throughput", "Op_Idx", "Op_Start_NS", "Op_End_NS"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    num_iters, durations, offsets = get_cluster_iteration_info(folder)
    segs = split_dataframe_by_drops(df, "Op_Start_NS", -100.0)
    num_csv_iters = len(segs)

    if iteration == "all":
        processed_segs = []
        for k, seg in enumerate(segs):
            off = offsets[k] if k < len(offsets) else 0.0
            seg = seg.copy()
            if off > 0:
                if "Op_Start_NS" in seg.columns:
                    seg["Op_Start_NS"] = seg["Op_Start_NS"] + off
                if "Op_End_NS" in seg.columns:
                    seg["Op_End_NS"] = seg["Op_End_NS"] + off
            processed_segs.append(seg)
        df_active = pd.concat(processed_segs, ignore_index=True)
    elif iteration == "last":
        df_active = segs[-1].copy()
    else:
        try:
            val = int(iteration) - 1
            idx = max(0, min(val, num_csv_iters - 1))
        except ValueError:
            idx = num_csv_iters - 1
        df_active = segs[idx].copy()

    df_active = df_active.dropna(subset=["Creation_Cycle", "Receive_Cycle"]).sort_values(by="PID", ascending=True).reset_index(drop=True)
    total_pkts = len(df_active)
    if total_pkts == 0:
        return {
            "has_data": False,
            "num_iterations": num_iters,
            "active_iteration": str(iteration),
            "total_packets": 0,
            "offset": 0,
            "limit": limit,
            "regime": regime,
            "packets": []
        }

    # Selección de régimen
    regime = str(regime).lower().strip()
    effective_offset = offset
    if regime == "free":
        effective_offset = 0
    elif regime == "medium":
        med_val = df_active["Total_Latency"].median()
        med_pos = int((df_active["Total_Latency"] - med_val).abs().values.argmin())
        effective_offset = max(0, med_pos - limit // 2)
    elif regime == "critical":
        max_pos = int(df_active["Total_Latency"].values.argmax())
        effective_offset = max(0, max_pos - limit // 2)
    else:
        effective_offset = max(0, min(offset, total_pkts - 1))

    limit = max(10, min(limit, 500))
    df_slice = df_active.iloc[effective_offset : effective_offset + limit]

    min_cycle = float(df_slice["Creation_Cycle"].min()) if not df_slice.empty else 0.0
    max_cycle = float(df_slice["Receive_Cycle"].max()) if not df_slice.empty else 1.0
    op_start_ns = float(df_slice["Op_Start_NS"].iloc[0]) if not df_slice.empty and "Op_Start_NS" in df_slice.columns else 0.0

    packets = []
    for _, row in df_slice.iterrows():
        c_cycle = float(row.get("Creation_Cycle", 0.0))
        inj_cycle = float(row.get("Inject_Cycle", c_cycle))
        rx_cycle = float(row.get("Receive_Cycle", inj_cycle))
        q_delay = float(row.get("Queueing_Delay", max(0.0, inj_cycle - c_cycle)))
        net_lat = float(row.get("Network_Latency", max(0.0, rx_cycle - inj_cycle)))
        tot_lat = float(row.get("Total_Latency", q_delay + net_lat))
        flits = int(row.get("Num_Flits", 9))
        size_b = int(row.get("Size_Bytes", flits * 32))
        avg_flit = float(row.get("Avg_Flit_Latency", tot_lat))
        prod = float(row.get("Throughput", 0.0))

        op_t = str(row.get("Op_Type", "Scatter"))
        op_i = int(row.get("Op_Idx", 1)) if not pd.isna(row.get("Op_Idx")) else 1
        p_op_start = float(row.get("Op_Start_NS", op_start_ns))
        p_op_end = float(row.get("Op_End_NS", p_op_start + tot_lat))

        global_create_ns = p_op_start + c_cycle
        global_inject_ns = p_op_start + inj_cycle
        global_receive_ns = p_op_start + rx_cycle

        packets.append({
            "pid": int(row.get("PID", 0)),
            "src": int(row.get("Source", 0)),
            "dst": int(row.get("Dest", 0)),
            "op_type": op_t,
            "op_idx": op_i,
            "flits": flits,
            "num_flits": flits,
            "size_bytes": size_b,
            "creation_cycle": c_cycle,
            "inject_cycle": inj_cycle,
            "receive_cycle": rx_cycle,
            "queueing_delay": q_delay,
            "queue_delay_cycles": q_delay,
            "network_latency": net_lat,
            "flight_cycles": net_lat,
            "total_latency": tot_lat,
            "total_latency_cycles": tot_lat,
            "avg_flit_latency": round(avg_flit, 2),
            "throughput": round(prod, 2),
            "op_start_ns": p_op_start,
            "op_end_ns": p_op_end,
            "global_create_ns": global_create_ns,
            "global_inject_ns": global_inject_ns,
            "global_receive_ns": global_receive_ns
        })

    return {
        "has_data": True,
        "clock_period_ns": 1.0,
        "num_iterations": num_iters,
        "active_iteration": str(iteration),
        "total_packets": total_pkts,
        "offset": effective_offset,
        "limit": limit,
        "regime": regime,
        "min_cycle": min_cycle,
        "max_cycle": max_cycle,
        "cycle_span": max_cycle - min_cycle,
        "packets": packets
    }


def get_packets_in_time_window(folder_path, start_ns, end_ns, iteration="last", max_packets=0):
    """
    Returns all in-flight packets whose lifecycle [pkt_start_ns, pkt_end_ns]
    overlaps with the visible time window [start_ns, end_ns] in global nanoseconds.
    If max_packets <= 0, returns 100% of packets without subsampling (zero truncation).
    If max_packets > 0 and packets exceed limit, applies uniform deterministic sampling.
    """
    folder = Path(folder_path).resolve()
    csv_path = folder / "packet_tracking_debug.csv"
    if not csv_path.exists():
        return {
            "has_data": False,
            "num_iterations": 1,
            "active_iteration": str(iteration),
            "start_ns": float(start_ns),
            "end_ns": float(end_ns),
            "total_in_window": 0,
            "returned": 0,
            "truncated": False,
            "packets": []
        }

    try:
        df = pd.read_csv(csv_path, on_bad_lines="skip")
        if df.empty or "Creation_Cycle" not in df.columns:
            return {
                "has_data": False,
                "num_iterations": 1,
                "active_iteration": str(iteration),
                "start_ns": float(start_ns),
                "end_ns": float(end_ns),
                "total_in_window": 0,
                "returned": 0,
                "truncated": False,
                "packets": []
            }

        df.columns = df.columns.str.strip()
        for col in ["PID", "Source", "Dest", "Creation_Cycle", "Inject_Cycle", "Receive_Cycle",
                    "Total_Latency", "Network_Latency", "Queueing_Delay", "Num_Flits",
                    "Op_Idx", "Op_Start_NS", "Op_End_NS"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        num_iters, durations, offsets = get_cluster_iteration_info(folder)
        segs = split_dataframe_by_drops(df, "Op_Start_NS", -100.0)

        # Determinar segmentos a procesar
        if iteration == "all":
            slices_to_process = [(k, segs[k], offsets[k] if k < len(offsets) else 0.0) for k in range(len(segs))]
        elif iteration == "last":
            slices_to_process = [(len(segs) - 1, segs[-1], 0.0)]
        else:
            try:
                val = int(iteration) - 1
                idx = max(0, min(val, len(segs) - 1))
            except ValueError:
                idx = len(segs) - 1
            slices_to_process = [(idx, segs[idx], 0.0)]

        matching_rows = []
        for k_iter, seg, off_ns in slices_to_process:
            seg = seg.dropna(subset=["Creation_Cycle", "Receive_Cycle"]).copy()
            if seg.empty:
                continue

            # Calcular ciclo base por colectiva
            base_cycles = seg.groupby(["Op_Type", "Op_Idx"])["Creation_Cycle"].transform("min")
            adjusted_op_start = seg["Op_Start_NS"] + off_ns

            seg["pkt_start_ns"] = adjusted_op_start + (seg["Creation_Cycle"] - base_cycles)
            seg["pkt_inject_ns"] = adjusted_op_start + (seg["Inject_Cycle"] - base_cycles)
            seg["pkt_end_ns"] = adjusted_op_start + (seg["Receive_Cycle"] - base_cycles)

            # Filtro de solapamiento con la ventana visible
            in_window = seg[(seg["pkt_end_ns"] >= start_ns) & (seg["pkt_start_ns"] <= end_ns)]
            if not in_window.empty:
                matching_rows.append(in_window)

        if not matching_rows:
            return {
                "has_data": True,
                "num_iterations": num_iters,
                "active_iteration": str(iteration),
                "start_ns": float(start_ns),
                "end_ns": float(end_ns),
                "total_in_window": 0,
                "returned": 0,
                "truncated": False,
                "packets": []
            }

        all_matching = pd.concat(matching_rows, ignore_index=True)
        all_matching = all_matching.sort_values(by=["pkt_start_ns", "PID"], ascending=[True, True]).reset_index(drop=True)
        total_in_window = len(all_matching)

        max_pkts = int(max_packets) if max_packets is not None else 0
        if max_pkts > 0 and total_in_window > max_pkts:
            limit_p = max(10, min(max_pkts, 5000))
            indices = np.linspace(0, total_in_window - 1, limit_p, dtype=int)
            sampled_df = all_matching.iloc[indices]
            truncated = True
        else:
            sampled_df = all_matching
            truncated = False

        packets = []
        for _, r in sampled_df.iterrows():
            c_cycle = float(r.get("Creation_Cycle", 0.0))
            inj_cycle = float(r.get("Inject_Cycle", c_cycle))
            rx_cycle = float(r.get("Receive_Cycle", inj_cycle))
            q_delay = float(r.get("Queueing_Delay", max(0.0, inj_cycle - c_cycle)))
            net_lat = float(r.get("Network_Latency", max(0.0, rx_cycle - inj_cycle)))
            tot_lat = float(r.get("Total_Latency", q_delay + net_lat))
            flits = int(r.get("Num_Flits", 9))

            packets.append({
                "pid": int(r["PID"]),
                "src": int(r["Source"]),
                "dst": int(r["Dest"]),
                "op_type": str(r.get("Op_Type", "Scatter")),
                "op_idx": int(r.get("Op_Idx", 1)) if pd.notna(r.get("Op_Idx")) else 1,
                "flits": flits,
                "queue_delay_cycles": round(q_delay, 1),
                "flight_cycles": round(net_lat, 1),
                "total_latency_cycles": round(tot_lat, 1),
                "pkt_start_ns": round(float(r["pkt_start_ns"]), 1),
                "pkt_inject_ns": round(float(r["pkt_inject_ns"]), 1),
                "pkt_end_ns": round(float(r["pkt_end_ns"]), 1),
            })

        return {
            "has_data": True,
            "num_iterations": num_iters,
            "active_iteration": str(iteration),
            "start_ns": float(start_ns),
            "end_ns": float(end_ns),
            "total_in_window": int(total_in_window),
            "returned": len(packets),
            "truncated": bool(truncated),
            "packets": packets
        }

    except Exception as e:
        print(f"⚠️ trace_parser: Error en get_packets_in_time_window: {e}")
        return {
            "has_data": False,
            "error": str(e),
            "num_iterations": 1,
            "active_iteration": str(iteration),
            "start_ns": float(start_ns),
            "end_ns": float(end_ns),
            "total_in_window": 0,
            "returned": 0,
            "truncated": False,
            "packets": []
        }


def infer_topology_links(topology, net_dims, num_gpus):
    """
    Computes physical NoC links (neighbors and wraparound) based on topology and dimensions.
    Returns: list of dicts {"src": int, "dst": int, "type": "neighbor"|"wraparound", "latency": int}
    """
    links = []
    topo = str(topology).lower().strip()
    net_dims_str = str(net_dims).strip()

    # 1. Torus 1D / Ring
    if topo in ["torus", "ring"] and ("x" not in net_dims_str and " " not in net_dims_str):
        n = num_gpus
        for i in range(n):
            nxt = (i + 1) % n
            is_wrap = (nxt == 0 and i == n - 1)
            lat = 2 if (is_wrap and topo == "torus") else 1
            link_type = "wraparound" if is_wrap else "neighbor"
            links.append({"src": i, "dst": nxt, "type": link_type, "latency": lat})
        return links

    # Check 3D (e.g. "2 2 2" or "2x2x2")
    m_dim3 = re.findall(r"\d+", net_dims_str)
    if len(m_dim3) == 3:
        kx, ky, kz = int(m_dim3[0]), int(m_dim3[1]), int(m_dim3[2])
        for z in range(kz):
            for y in range(ky):
                for x in range(kx):
                    node_id = z * (kx * ky) + y * kx + x
                    if node_id >= num_gpus:
                        continue
                    if x + 1 < kx:
                        r_id = z * (kx * ky) + y * kx + (x + 1)
                        if r_id < num_gpus:
                            links.append({"src": node_id, "dst": r_id, "type": "neighbor", "latency": 1})
                    if y + 1 < ky:
                        d_id = z * (kx * ky) + (y + 1) * kx + x
                        if d_id < num_gpus:
                            links.append({"src": node_id, "dst": d_id, "type": "neighbor", "latency": 1})
                    if z + 1 < kz:
                        z_id = (z + 1) * (kx * ky) + y * kx + x
                        if z_id < num_gpus:
                            links.append({"src": node_id, "dst": z_id, "type": "neighbor", "latency": 1})
        return links

    # 2. Mesh 2D / Torus 2D
    m_dim = re.search(r"(\d+)[x\s](\d+)", net_dims_str)
    if m_dim:
        kx = int(m_dim.group(1))
        ky = int(m_dim.group(2))
    else:
        if num_gpus == 8:
            kx, ky = 4, 2
        elif num_gpus == 4:
            kx, ky = 2, 2
        elif num_gpus == 16:
            kx, ky = 4, 4
        else:
            kx, ky = num_gpus, 1

    if ky == 1:
        for i in range(num_gpus):
            if i + 1 < num_gpus:
                links.append({"src": i, "dst": i + 1, "type": "neighbor", "latency": 1})
            elif topo == "torus":
                links.append({"src": i, "dst": 0, "type": "wraparound", "latency": 2})
        return links

    for y in range(ky):
        for x in range(kx):
            node_id = y * kx + x
            if node_id >= num_gpus:
                continue

            # Horizontal neighbor (X+1)
            if x + 1 < kx:
                right_id = y * kx + (x + 1)
                if right_id < num_gpus:
                    links.append({"src": node_id, "dst": right_id, "type": "neighbor", "latency": 1})
            elif topo == "torus" and kx > 2:
                wrap_x_id = y * kx + 0
                if wrap_x_id < num_gpus:
                    links.append({"src": node_id, "dst": wrap_x_id, "type": "wraparound", "latency": 2})

            # Vertical neighbor (Y+1)
            if y + 1 < ky:
                down_id = (y + 1) * kx + x
                if down_id < num_gpus:
                    links.append({"src": node_id, "dst": down_id, "type": "neighbor", "latency": 1})
            elif topo == "torus" and ky > 2:
                wrap_y_id = 0 * kx + x
                if wrap_y_id < num_gpus:
                    links.append({"src": node_id, "dst": wrap_y_id, "type": "wraparound", "latency": 2})

    return links


def _compute_routing_path(src, dst, topology, dims_str, num_gpus, adj_list=None):
    """
    Computes deterministic routing path (list of node IDs) between src and dst.
    - Torus/Ring 1D: shortest circular path (wraparound when circular distance < linear).
    - Torus/Mesh 2D & 3D: Dimension-Order Routing (DOR: dim 0 -> dim 1 -> dim 2).
    - General / AnyNet: BFS shortest path over adjacency list.
    """
    if src == dst:
        return [src]

    topo = str(topology).lower().strip()
    dims = str(dims_str).strip()

    # 1. Torus 1D / Ring
    if topo in ["torus", "ring"] and ("x" not in dims and " " not in dims):
        n = num_gpus
        d_fwd = (dst - src) % n
        d_bwd = (src - dst) % n
        path = [src]
        curr = src
        if d_fwd <= d_bwd:
            while curr != dst:
                curr = (curr + 1) % n
                path.append(curr)
        else:
            while curr != dst:
                curr = (curr - 1) % n
                path.append(curr)
        return path

    # 2. Check 3D Mesh / Torus
    m3 = [int(x) for x in re.findall(r"\d+", dims)]
    if len(m3) == 3 and m3[0] * m3[1] * m3[2] == num_gpus:
        kx, ky, kz = m3[0], m3[1], m3[2]
        x1 = (src % (kx * ky)) % kx
        y1 = (src % (kx * ky)) // kx
        z1 = src // (kx * ky)

        x2 = (dst % (kx * ky)) % kx
        y2 = (dst % (kx * ky)) // kx
        z2 = dst // (kx * ky)

        cx, cy, cz = x1, y1, z1
        path = [src]

        # X dim
        if topo == "torus" and kx > 2:
            d_fwd = (x2 - cx) % kx
            d_bwd = (cx - x2) % kx
            step = 1 if d_fwd <= d_bwd else -1
            while cx != x2:
                cx = (cx + step) % kx
                path.append(cz * (kx * ky) + cy * kx + cx)
        else:
            step = 1 if x2 >= cx else -1
            while cx != x2:
                cx += step
                path.append(cz * (kx * ky) + cy * kx + cx)

        # Y dim
        if topo == "torus" and ky > 2:
            d_fwd = (y2 - cy) % ky
            d_bwd = (cy - y2) % ky
            step = 1 if d_fwd <= d_bwd else -1
            while cy != y2:
                cy = (cy + step) % ky
                path.append(cz * (kx * ky) + cy * kx + cx)
        else:
            step = 1 if y2 >= cy else -1
            while cy != y2:
                cy += step
                path.append(cz * (kx * ky) + cy * kx + cx)

        # Z dim
        if topo == "torus" and kz > 2:
            d_fwd = (z2 - cz) % kz
            d_bwd = (cz - z2) % kz
            step = 1 if d_fwd <= d_bwd else -1
            while cz != z2:
                cz = (cz + step) % kz
                path.append(cz * (kx * ky) + cy * kx + cx)
        else:
            step = 1 if z2 >= cz else -1
            while cz != z2:
                cz += step
                path.append(cz * (kx * ky) + cy * kx + cx)

        return path

    # 3. 2D Mesh / Torus
    m2 = [int(x) for x in re.findall(r"\d+", dims)]
    if len(m2) >= 2:
        kx, ky = m2[0], m2[1]
    else:
        if num_gpus == 8:
            kx, ky = 4, 2
        elif num_gpus == 4:
            kx, ky = 2, 2
        elif num_gpus == 16:
            kx, ky = 4, 4
        else:
            kx, ky = num_gpus, 1

    if ky > 1:
        x1, y1 = src % kx, src // kx
        x2, y2 = dst % kx, dst // kx
        cx, cy = x1, y1
        path = [src]

        # X dim
        if topo == "torus" and kx > 2:
            d_fwd = (x2 - cx) % kx
            d_bwd = (cx - x2) % kx
            step = 1 if d_fwd <= d_bwd else -1
            while cx != x2:
                cx = (cx + step) % kx
                path.append(cy * kx + cx)
        else:
            step = 1 if x2 >= cx else -1
            while cx != x2:
                cx += step
                path.append(cy * kx + cx)

        # Y dim
        if topo == "torus" and ky > 2:
            d_fwd = (y2 - cy) % ky
            d_bwd = (cy - y2) % ky
            step = 1 if d_fwd <= d_bwd else -1
            while cy != y2:
                cy = (cy + step) % ky
                path.append(cy * kx + cx)
        else:
            step = 1 if y2 >= cy else -1
            while cy != y2:
                cy += step
                path.append(cy * kx + cx)

        return path

    # 4. Fallback: BFS over adjacency list
    if adj_list:
        from collections import deque
        q = deque([[src]])
        visited = {src}
        while q:
            p = q.popleft()
            u = p[-1]
            if u == dst:
                return p
            for v in sorted(adj_list.get(u, [])):
                if v not in visited:
                    visited.add(v)
                    q.append(p + [v])

    return [src, dst]


def get_node_expert_label(model_name, node_id, num_gpus):
    """Returns a descriptive string of expert assignments for node_id."""
    m = str(model_name).lower()
    if "deepseek" in m:
        if num_gpus > 0:
            exp_per_gpu = max(1, 256 // num_gpus)
            s_exp = node_id * exp_per_gpu
            e_exp = min(255, (node_id + 1) * exp_per_gpu - 1)
            return f"Exp #{s_exp}..#{e_exp} + Shared"
        return "256 Micro-Exp + Shared"
    elif "mixtral" in m:
        if num_gpus == 8:
            return f"Exp #{node_id}"
        elif num_gpus == 4:
            return f"Exp #{node_id * 2}, #{node_id * 2 + 1}"
        elif num_gpus == 2:
            return f"Exp #{node_id * 4}..#{node_id * 4 + 3}"
        elif num_gpus == 1:
            return "Exp #0..#7"
        else:
            return f"Exp #{node_id}"
    elif "llama" in m:
        return "Denso (Sin MoE)"
    return f"GPU {node_id}"


def get_topology_traffic_data(folder_path=None, iteration="last", op_filter="all", preview_params=None):
    """
    Computes NoC topological graph, per-GPU traffic heatmap, and inter-node communication flows.
    Supports real simulation folders or interactive preview mode from Tab 1.
    """
    if not folder_path and preview_params:
        topo = str(preview_params.get("topology", "torus")).lower()
        net_dims = str(preview_params.get("net_dims", "8"))
        num_gpus = int(preview_params.get("num_gpus", 8))
        model = str(preview_params.get("model", "mixtral"))
        links = infer_topology_links(topo, net_dims, num_gpus)
        for l in links:
            l["packets"] = 0
            l["flits"] = 0
            l["share_pct"] = 0.0
            l["tx_u_to_v_pkts"] = 0
            l["tx_v_to_u_pkts"] = 0
            l["avg_queueing_delay"] = 0.0
            l["avg_network_latency"] = 0.0
            l["avg_stall_us"] = 0.0

        nodes = []
        for d in range(num_gpus):
            nodes.append({
                "id": d,
                "label": f"GPU {d}",
                "experts": get_node_expert_label(model, d, num_gpus),
                "tx_packets": 0,
                "tx_flits": 0,
                "tx_share_pct": 0.0,
                "rx_packets": 0,
                "rx_flits": 0,
                "rx_share_pct": 0.0,
                "avg_queueing_delay": 0.0,
                "avg_total_latency": 0.0,
                "compute_us": 0.0,
                "transit_us": 0.0,
                "stall_us": 0.0
            })
        return {
            "success": True,
            "preview_mode": True,
            "has_packet_data": False,
            "folder_name": "(Vista Previa)",
            "model": model,
            "topology": topo,
            "net_dims": net_dims,
            "num_gpus": num_gpus,
            "batch_size": preview_params.get("batch_size", 32),
            "skewness": preview_params.get("skewness", 0.0),
            "tensor_degree": preview_params.get("tensor_degree", 1),
            "vcs": preview_params.get("vcs", 4),
            "routing": preview_params.get("routing", "dim_order"),
            "num_iterations": 1,
            "active_iteration": str(iteration),
            "active_op_filter": str(op_filter),
            "total_packets": 0,
            "total_flits": 0,
            "nodes": nodes,
            "flows": [],
            "links": links
        }

    folder = Path(folder_path).resolve()
    if not folder.exists():
        raise FileNotFoundError(f"Carpeta no encontrada: {folder_path}")

    # 1. Metadatos de la simulación
    summary = get_simulation_summary(folder, iteration=iteration)
    meta = summary.get("metadata", {})
    model = meta.get("model", "mixtral")
    topo = meta.get("topology", "torus")
    net_dims = meta.get("net_dims", str(meta.get("num_gpus", 8)))
    num_gpus = meta.get("num_gpus", 8)
    num_iters = summary.get("num_iterations", 1)

    # 2. Enlaces físicos
    links = infer_topology_links(topo, net_dims, num_gpus)
    adj_list = {}
    for l in links:
        u, v = l["src"], l["dst"]
        if u not in adj_list: adj_list[u] = []
        if v not in adj_list: adj_list[v] = []
        adj_list[u].append(v)
        adj_list[v].append(u)

    link_stats = {}
    for l in links:
        lk = tuple(sorted((l["src"], l["dst"])))
        link_stats[lk] = {
            "packets": 0,
            "flits": 0,
            "tx_u_to_v_pkts": 0,
            "tx_v_to_u_pkts": 0,
            "weighted_queue_sum": 0.0,
            "weighted_net_lat_sum": 0.0,
        }

    # 3. Tiempos de cómputo, red y stall por GPU desde archivos .trc
    _, durations, _ = get_cluster_iteration_info(folder)
    if iteration == "all":
        target_iter_mode = "all"
    elif iteration == "last":
        target_iter_mode = num_iters - 1
    else:
        try:
            val = int(iteration) - 1
            target_iter_mode = max(0, min(val, num_iters - 1))
        except ValueError:
            target_iter_mode = num_iters - 1

    gpu_times = {}
    for d in range(num_gpus):
        gpu_times[d] = {"compute_us": 0.0, "transit_us": 0.0, "stall_us": 0.0}

    trc_pattern = str(folder / "*device_*.trc")
    for tf in glob.glob(trc_pattern):
        try:
            basename = os.path.basename(tf)
            d_id = int(basename.split("_")[-1].split(".")[0])
            df_t = pd.read_csv(tf, on_bad_lines="skip")
            df_t.columns = df_t.columns.str.strip()
            df_t["START_NS"] = pd.to_numeric(df_t["START_NS"], errors="coerce")
            df_t["DURATION"] = pd.to_numeric(df_t["DURATION"], errors="coerce")
            df_t = df_t.dropna(subset=["START_NS", "DURATION"])
            df_t = df_t[df_t["DURATION"] > 0]
            if df_t.empty:
                continue

            segs = split_dataframe_by_drops(df_t, "START_NS", -1.0)
            if target_iter_mode == "all":
                df_act = pd.concat(segs, ignore_index=True)
            else:
                s_idx = min(target_iter_mode, len(segs) - 1)
                df_act = segs[s_idx]

            df_act["TYPE"] = df_act["TYPE"].astype(str).str.strip().str.lower()
            scat = df_act[df_act["TYPE"].str.contains("scatter")]["DURATION"].sum()
            gath = df_act[df_act["TYPE"].str.contains("gather")]["DURATION"].sum()
            ar = df_act[df_act["TYPE"].str.contains("all_reduce|allreduce")]["DURATION"].sum()
            trans = scat + gath + ar
            stl = df_act[df_act["TYPE"].str.contains("stall")]["DURATION"].sum()
            non_comp = df_act["TYPE"].str.contains("scatter|gather|stall|all_reduce|allreduce")
            comp = df_act[~non_comp]["DURATION"].sum()

            gpu_times[d_id] = {
                "compute_us": round(float(comp) / 1000.0, 2),
                "transit_us": round(float(trans) / 1000.0, 2),
                "stall_us": round(float(stl) / 1000.0, 2)
            }
        except Exception:
            pass

    # 4. Datos de paquetes NoC desde packet_tracking_debug.csv
    csv_path = folder / "packet_tracking_debug.csv"
    has_packet_data = csv_path.exists()
    flows = []
    total_slice_packets = 0
    total_slice_flits = 0

    tx_stats = {d: {"pkts": 0, "flits": 0, "q_avg": 0.0} for d in range(num_gpus)}
    rx_stats = {d: {"pkts": 0, "flits": 0, "lat_avg": 0.0} for d in range(num_gpus)}

    if has_packet_data:
        try:
            # Lectura optimizada seleccionando solo columnas necesarias
            usecols = ["Source", "Dest", "Num_Flits", "Queueing_Delay", "Total_Latency", "Network_Latency", "Op_Type", "Op_Start_NS"]
            first_line = pd.read_csv(csv_path, nrows=2)
            valid_cols = [c.strip() for c in first_line.columns if c.strip() in usecols or c.strip() in ["Latency", "Network_Latency"]]
            df_p = pd.read_csv(csv_path, usecols=valid_cols, on_bad_lines="skip")
            if not df_p.empty and "Source" in df_p.columns and "Dest" in df_p.columns:
                df_p.columns = df_p.columns.str.strip()
                for c in ["Source", "Dest", "Num_Flits", "Queueing_Delay", "Total_Latency", "Network_Latency", "Op_Start_NS"]:
                    if c in df_p.columns:
                        df_p[c] = pd.to_numeric(df_p[c], errors="coerce")

                if "Num_Flits" not in df_p.columns:
                    df_p["Num_Flits"] = 9
                if "Queueing_Delay" not in df_p.columns:
                    df_p["Queueing_Delay"] = 0.0
                if "Total_Latency" not in df_p.columns:
                    df_p["Total_Latency"] = df_p.get("Latency", 0.0)
                if "Network_Latency" not in df_p.columns:
                    df_p["Network_Latency"] = (df_p["Total_Latency"] - df_p["Queueing_Delay"]).clip(lower=0)

                # Segmentación por iteración
                segs_p = split_dataframe_by_drops(df_p, "Op_Start_NS", -100.0)
                if target_iter_mode == "all":
                    df_slice = pd.concat(segs_p, ignore_index=True)
                else:
                    c_idx = min(target_iter_mode, len(segs_p) - 1)
                    df_slice = segs_p[c_idx]

                df_slice = df_slice.dropna(subset=["Source", "Dest"])

                # Filtro por fase de operación colectiva
                f_op = op_filter.lower().strip()
                if f_op in ["scatter", "moe scatter"]:
                    df_filtered = df_slice[df_slice["Op_Type"].astype(str).str.contains("scatter", case=False, na=False)]
                elif f_op in ["gather", "moe gather"]:
                    df_filtered = df_slice[df_slice["Op_Type"].astype(str).str.contains("gather", case=False, na=False)]
                elif f_op in ["allreduce", "ring-allreduce", "all_reduce"]:
                    df_filtered = df_slice[df_slice["Op_Type"].astype(str).str.contains("all_reduce|allreduce", case=False, na=False)]
                else:
                    df_filtered = df_slice

                total_slice_packets = len(df_filtered)
                total_slice_flits = int(df_filtered["Num_Flits"].sum()) if total_slice_packets > 0 else 0

                # Agregación vectorizada ultra-rápida por nodo
                if total_slice_packets > 0:
                    tx_grp = df_filtered.groupby("Source")
                    tx_pkts_s = tx_grp.size()
                    tx_flits_s = tx_grp["Num_Flits"].sum() if "Num_Flits" in df_filtered else tx_pkts_s * 9
                    tx_q_s = tx_grp["Queueing_Delay"].mean() if "Queueing_Delay" in df_filtered else None

                    rx_grp = df_filtered.groupby("Dest")
                    rx_pkts_s = rx_grp.size()
                    rx_flits_s = rx_grp["Num_Flits"].sum() if "Num_Flits" in df_filtered else rx_pkts_s * 9
                    rx_lat_s = rx_grp["Total_Latency"].mean() if "Total_Latency" in df_filtered else None

                    for d in range(num_gpus):
                        p_tx = int(tx_pkts_s.get(d, 0))
                        f_tx = int(tx_flits_s.get(d, 0))
                        q_tx = float(tx_q_s.get(d, 0.0)) if tx_q_s is not None and d in tx_q_s else 0.0

                        p_rx = int(rx_pkts_s.get(d, 0))
                        f_rx = int(rx_flits_s.get(d, 0))
                        l_rx = float(rx_lat_s.get(d, 0.0)) if rx_lat_s is not None and d in rx_lat_s else 0.0

                        tx_stats[d] = {"pkts": p_tx, "flits": f_tx, "q_avg": round(q_tx, 1)}
                        rx_stats[d] = {"pkts": p_rx, "flits": f_rx, "lat_avg": round(l_rx, 1)}

                    # Agregación vectorizada de flujos (Source -> Dest con s != d)
                    flow_df = df_filtered[df_filtered["Source"] != df_filtered["Dest"]]
                    if not flow_df.empty:
                        flow_grp = flow_df.groupby(["Source", "Dest"]).agg(
                            packets=("Num_Flits", "count"),
                            flits=("Num_Flits", "sum"),
                            avg_latency=("Total_Latency", "mean") if "Total_Latency" in flow_df else ("Num_Flits", lambda _: 0.0),
                            avg_queue=("Queueing_Delay", "mean") if "Queueing_Delay" in flow_df else ("Num_Flits", lambda _: 0.0),
                            max_queue=("Queueing_Delay", "max") if "Queueing_Delay" in flow_df else ("Num_Flits", lambda _: 0.0),
                            avg_net_lat=("Network_Latency", "mean") if "Network_Latency" in flow_df else ("Num_Flits", lambda _: 0.0),
                        ).reset_index()

                        for _, f_row in flow_grp.iterrows():
                            s = int(f_row["Source"])
                            d = int(f_row["Dest"])
                            cnt = int(f_row["packets"])
                            f_sum = int(f_row["flits"])
                            lat_m = float(f_row["avg_latency"]) if pd.notna(f_row["avg_latency"]) else 0.0
                            q_m = float(f_row["avg_queue"]) if pd.notna(f_row["avg_queue"]) else 0.0
                            q_max = float(f_row["max_queue"]) if pd.notna(f_row["max_queue"]) else 0.0
                            net_m = float(f_row["avg_net_lat"]) if pd.notna(f_row["avg_net_lat"]) else max(0.0, lat_m - q_m)
                            sh_pct = round((cnt / total_slice_packets * 100.0), 2)

                            route_path = _compute_routing_path(s, d, topo, net_dims, num_gpus, adj_list)
                            hops = max(1, len(route_path) - 1)

                            flows.append({
                                "src": s,
                                "dst": d,
                                "packets": cnt,
                                "flits": f_sum,
                                "avg_latency": round(lat_m, 1),
                                "avg_total_latency": round(lat_m, 1),
                                "avg_queue": round(q_m, 1),
                                "avg_queueing_delay": round(q_m, 1),
                                "max_queueing_delay": round(q_max, 1),
                                "avg_network_latency": round(net_m, 1),
                                "hops": hops,
                                "share_pct": sh_pct,
                                "path": route_path
                            })

                            # Proyección sobre enlaces físicos atravesados
                            for i in range(len(route_path) - 1):
                                step_u = route_path[i]
                                step_v = route_path[i + 1]
                                lk = tuple(sorted((step_u, step_v)))
                                if lk in link_stats:
                                    link_stats[lk]["packets"] += cnt
                                    link_stats[lk]["flits"] += f_sum
                                    if step_u < step_v:
                                        link_stats[lk]["tx_u_to_v_pkts"] += cnt
                                    else:
                                        link_stats[lk]["tx_v_to_u_pkts"] += cnt
                                    link_stats[lk]["weighted_queue_sum"] += q_m * cnt
                                    link_stats[lk]["weighted_net_lat_sum"] += net_m * cnt

                        flows.sort(key=lambda x: x["packets"], reverse=True)
        except Exception as e:
            print(f"⚠️ trace_parser: Error en get_topology_traffic_data: {e}")

    # 5. Poblado de métricas en enlaces físicos
    for l in links:
        lk = tuple(sorted((l["src"], l["dst"])))
        st = link_stats.get(lk, {
            "packets": 0, "flits": 0, "tx_u_to_v_pkts": 0, "tx_v_to_u_pkts": 0,
            "weighted_queue_sum": 0.0, "weighted_net_lat_sum": 0.0
        })
        l_pkts = st["packets"]
        l_flits = st["flits"]
        l_sh = round((l_pkts / total_slice_packets * 100.0), 2) if total_slice_packets > 0 else 0.0
        l_q = round(st["weighted_queue_sum"] / l_pkts, 1) if l_pkts > 0 else 0.0
        l_net_lat = round(st["weighted_net_lat_sum"] / l_pkts, 1) if l_pkts > 0 else 0.0
        u_stall = gpu_times.get(lk[0], {}).get("stall_us", 0.0)
        v_stall = gpu_times.get(lk[1], {}).get("stall_us", 0.0)
        l_stall = round((u_stall + v_stall) / 2.0, 1)

        l["packets"] = l_pkts
        l["flits"] = l_flits
        l["share_pct"] = l_sh
        l["tx_u_to_v_pkts"] = st["tx_u_to_v_pkts"]
        l["tx_v_to_u_pkts"] = st["tx_v_to_u_pkts"]
        l["avg_queueing_delay"] = l_q
        l["avg_network_latency"] = l_net_lat
        l["avg_stall_us"] = l_stall

    # 6. Ensamblado de nodos
    nodes = []
    for d in range(num_gpus):
        tx_p = tx_stats[d]["pkts"]
        tx_f = tx_stats[d]["flits"]
        rx_p = rx_stats[d]["pkts"]
        rx_f = rx_stats[d]["flits"]

        tx_pct = round((tx_p / total_slice_packets * 100.0), 2) if total_slice_packets > 0 else 0.0
        rx_pct = round((rx_p / total_slice_packets * 100.0), 2) if total_slice_packets > 0 else 0.0

        q_avg = tx_stats[d].get("q_avg", 0.0)
        lat_avg = rx_stats[d].get("lat_avg", 0.0)

        t_info = gpu_times.get(d, {"compute_us": 0.0, "transit_us": 0.0, "stall_us": 0.0})

        nodes.append({
            "id": d,
            "label": f"GPU {d}",
            "experts": get_node_expert_label(model, d, num_gpus),
            "tx_packets": tx_p,
            "tx_flits": tx_f,
            "tx_share_pct": tx_pct,
            "rx_packets": rx_p,
            "rx_flits": rx_f,
            "rx_share_pct": rx_pct,
            "avg_queueing_delay": q_avg,
            "avg_total_latency": lat_avg,
            "compute_us": t_info["compute_us"],
            "transit_us": t_info["transit_us"],
            "stall_us": t_info["stall_us"]
        })

    return {
        "success": True,
        "preview_mode": False,
        "has_packet_data": bool(has_packet_data and total_slice_packets > 0),
        "folder_name": folder.name,
        "model": model,
        "topology": topo,
        "net_dims": str(net_dims),
        "num_gpus": num_gpus,
        "batch_size": meta.get("batch_size", 32),
        "skewness": meta.get("skewness", 0.0),
        "tensor_degree": meta.get("tensor_degree", 1),
        "vcs": meta.get("vcs", 4),
        "routing": meta.get("routing", "dim_order"),
        "num_iterations": num_iters,
        "active_iteration": str(iteration),
        "active_op_filter": str(op_filter),
        "total_packets": int(total_slice_packets),
        "total_flits": int(total_slice_flits),
        "nodes": nodes,
        "flows": flows,
        "links": links
    }
