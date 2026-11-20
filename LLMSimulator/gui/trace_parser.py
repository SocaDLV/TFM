# -*- coding: utf-8 -*-
"""
Trace and Packet Tracking Parser for LLM-NoC Co-Simulation Workbench.
Reconstructs cycle-to-cycle GPU chronograms, packet flight data, and macroscopic KPIs
directly from raw files (.trc and packet_tracking_debug.csv) without generating static PNGs.
"""

import os
import glob
import re
import json
import numpy as np
import pandas as pd
from pathlib import Path


def load_network_ops_debug(folder_path):
    """
    Loads packet_tracking_debug.csv, applies anti-appends filter to isolate the steady-state
    iteration, and aggregates statistics per network collective and per GPU.
    """
    csv_path = os.path.join(folder_path, "packet_tracking_debug.csv")
    if not os.path.exists(csv_path):
        return []

    try:
        df_p = pd.read_csv(csv_path, on_bad_lines="skip")
        if df_p.empty or "Op_Type" not in df_p.columns:
            return []

        df_p.columns = df_p.columns.str.strip()

        # Anti-appends filter
        if "Op_Start_NS" in df_p.columns and not df_p["Op_Start_NS"].isna().all():
            drops = df_p["Op_Start_NS"].diff() < 0
            if drops.any():
                last_drop_idx = drops[drops].index[-1]
                df_p = df_p.loc[last_drop_idx:].copy()
        elif "Creation_Cycle" in df_p.columns:
            drops = df_p["Creation_Cycle"].diff() < -1000
            if drops.any():
                last_drop_idx = drops[drops].index[-1]
                df_p = df_p.loc[last_drop_idx:].copy()

        all_nodes = set()
        if "Source" in df_p.columns:
            all_nodes.update(df_p["Source"].dropna().unique())
        if "Dest" in df_p.columns:
            all_nodes.update(df_p["Dest"].dropna().unique())
        max_node = int(max(all_nodes)) if all_nodes else 7
        num_gpus = max(8, max_node + 1)

        ops = []
        for (op_type, op_idx), grp in df_p.groupby(["Op_Type", "Op_Idx"], sort=False):
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


def get_simulation_summary(folder_path):
    """
    Computes macroscopic KPIs and architecture metadata for a simulation folder
    isolating the last iteration.
    """
    folder = Path(folder_path).resolve()
    if not folder.exists():
        raise FileNotFoundError(f"Carpeta no encontrada: {folder_path}")

    # 1. Metadatos de config.yaml, test.cfg y gui_metadata.json
    metadata = {
        "folder_name": folder.name,
        "model": "mixtral",
        "topology": "torus",
        "net_dims": "8",
        "num_gpus": 8,
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
            with open(test_cfg, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("topology"):
                        metadata["topology"] = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("routing_function"):
                        metadata["routing"] = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("num_vcs"):
                        metadata["vcs"] = int(line.split("=")[1].replace(";", "").strip())
        except Exception:
            pass

    # 2. Análisis macroscópico de archivos .trc
    trc_files = glob.glob(str(folder / "*device_*.trc"))
    compute_total = 0.0
    transit_total = 0.0
    stall_total = 0.0
    scatter_total = 0.0
    gather_total = 0.0
    allreduce_total = 0.0
    devices_counted = 0
    min_cluster_start = float("inf")
    max_cluster_end = 0.0

    for trc_path in sorted(trc_files):
        try:
            df = pd.read_csv(trc_path, on_bad_lines="skip")
            df.columns = df.columns.str.strip()
            df["START_NS"] = pd.to_numeric(df["START_NS"], errors="coerce")
            df["END_NS"] = pd.to_numeric(df["END_NS"], errors="coerce")
            df["DURATION"] = pd.to_numeric(df["DURATION"], errors="coerce")
            df = df.dropna(subset=["START_NS", "END_NS", "DURATION"])

            drops = df["START_NS"].diff() < 0
            if drops.any():
                last_drop_idx = drops[drops].index[-1]
                df = df.loc[last_drop_idx:].copy()

            df = df[df["DURATION"] > 0]
            if df.empty:
                continue

            dev_start = df["START_NS"].min()
            dev_end = df["END_NS"].max()
            min_cluster_start = min(min_cluster_start, dev_start)
            max_cluster_end = max(max_cluster_end, dev_end)

            df["TYPE"] = df["TYPE"].astype(str).str.strip().str.lower()
            scatter = df[df["TYPE"].str.contains("scatter")]["DURATION"].sum()
            gather = df[df["TYPE"].str.contains("gather")]["DURATION"].sum()
            all_red = df[df["TYPE"].str.contains("all_reduce|allreduce")]["DURATION"].sum()
            transit = scatter + gather + all_red

            stall = df[df["TYPE"].str.contains("stall")]["DURATION"].sum()
            non_comp_mask = df["TYPE"].str.contains("scatter|gather|stall|all_reduce|allreduce")
            compute = df[~non_comp_mask]["DURATION"].sum()

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
    cluster_wall_clock_ns = max_cluster_end - min_cluster_start if max_cluster_end > min_cluster_start else 0.0
    c_avg_ns = compute_total / devices_counted if devices_counted > 0 else 0.0
    t_avg_ns = transit_total / devices_counted if devices_counted > 0 else 0.0
    s_avg_ns = stall_total / devices_counted if devices_counted > 0 else 0.0
    scat_avg_ns = scatter_total / devices_counted if devices_counted > 0 else 0.0
    gath_avg_ns = gather_total / devices_counted if devices_counted > 0 else 0.0
    ar_avg_ns = allreduce_total / devices_counted if devices_counted > 0 else 0.0

    # 3. Métricas de packet_tracking_debug.csv
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
                # Anti-appends filter
                if "Op_Start_NS" in df_p.columns and not df_p["Op_Start_NS"].isna().all():
                    drops = df_p["Op_Start_NS"].diff() < 0
                    if drops.any():
                        last_reset = drops[drops].index[-1]
                        df_p = df_p.loc[last_reset:].copy()
                elif "Creation_Cycle" in df_p.columns:
                    drops = df_p["Creation_Cycle"].diff() < -1000
                    if drops.any():
                        last_reset = drops[drops].index[-1]
                        df_p = df_p.loc[last_reset:].copy()

                df_p = df_p.dropna(subset=["Creation_Cycle", "Receive_Cycle"])
                total_packets = len(df_p)
                if "Num_Flits" in df_p.columns:
                    total_flits = int(df_p["Num_Flits"].sum())
                else:
                    total_flits = total_packets * 9

                if total_packets > 0:
                    dur_cycles = max(1.0, float(df_p["Receive_Cycle"].max() - df_p["Creation_Cycle"].min()))
                    lambda_rate = total_flits / (num_gpus * dur_cycles)
                    if "Avg_Flit_Latency" in df_p.columns:
                        avg_flit_lat = float(df_p["Avg_Flit_Latency"].mean())
                    if "Total_Latency" in df_p.columns:
                        avg_pkt_lat = float(df_p["Total_Latency"].mean())
                    if "Queueing_Delay" in df_p.columns:
                        avg_queue_delay = float(df_p["Queueing_Delay"].mean())
        except Exception as e:
            print(f"⚠️ trace_parser: Error leyendo CSV en summary: {e}")

    # Ratios porcentuales
    tot_ref = float(cluster_wall_clock_ns) if cluster_wall_clock_ns > 0 else float(c_avg_ns + t_avg_ns + s_avg_ns)
    c_pct = (float(c_avg_ns) / tot_ref * 100.0) if tot_ref > 0 else 0.0
    t_pct = (float(t_avg_ns) / tot_ref * 100.0) if tot_ref > 0 else 0.0
    s_pct = (float(s_avg_ns) / tot_ref * 100.0) if tot_ref > 0 else 0.0

    kpis_data = {
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
        "scatter_us": round(float(scat_avg_ns) / 1000.0, 2),
        "gather_us": round(float(gath_avg_ns) / 1000.0, 2),
        "allreduce_us": round(float(ar_avg_ns) / 1000.0, 2),
        "real_injection_rate_lambda": round(float(lambda_rate), 4),
        "lambda_rate": round(float(lambda_rate), 4),
        "avg_flit_lat_cycles": round(float(avg_flit_lat), 1),
        "avg_flit_latency": round(float(avg_flit_lat), 1),
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
        **kpis_data
    }


def parse_single_trc(filepath):
    """Parses a single .trc file, extracts layers, classifies sub-ops, and coalesces blocks."""
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

    # Anti-appends filter
    drops = df["START_NS"].diff() < 0
    if drops.any():
        last_drop_idx = drops[drops].index[-1]
        df = df.loc[last_drop_idx:].copy()

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

        # Shared Expert
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

        # Routed Experts
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

        # Dense FFN
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

        # Attention
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
        start_ns = float(grp["START_NS"].min())
        end_ns = float(grp["END_NS"].max())
        dur_ns = end_ns - start_ns
        category = first_row["CATEGORY"]
        color = first_row["COLOR"]
        macro_op = first_row["MACRO_OP"]
        layer = int(first_row["LAYER"])

        # Fronteras internas de micro-operaciones
        sub_ops = []
        for _, r in grp.iloc[:-1].iterrows():
            if r["DURATION"] > 0.5:
                sub_ops.append({
                    "end_ns": float(r["END_NS"]),
                    "name": str(r["MICRO_OP"])
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
            mem_bound_pct = round((tot_mem / (tot_comp + tot_mem)) * 100.0, 1)

        title = f"Layer {layer} | {macro_op}"
        if category == "stall":
            title = f"Layer {layer} | Stall"
        elif category == "all_reduce":
            title = f"Layer {layer} | AllReduce"

        blocks.append({
            "gpu_id": gpu_id,
            "layer": layer,
            "category": category,
            "color": color,
            "macro_op": macro_op,
            "title": title,
            "subtitle": seq_str,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "duration_ns": dur_ns,
            "mem_bound_pct": mem_bound_pct,
            "sub_ops": sub_ops,
            "local_net": None
        })

    return blocks


def get_chronogram_data(folder_path):
    """
    Parses all .trc files in folder, applies network ops matching per GPU,
    and returns a consolidated timeline for HTML5 Canvas rendering.
    """
    folder = Path(folder_path).resolve()
    trc_files = glob.glob(str(folder / "*device_*.trc"))
    if not trc_files:
        raise FileNotFoundError(f"No se encontraron ficheros *device_*.trc en: {folder_path}")

    network_ops = load_network_ops_debug(folder_path)

    all_blocks = []
    for tf in sorted(trc_files):
        blocks = parse_single_trc(tf)
        all_blocks.extend(blocks)

    if not all_blocks:
        return {"num_gpus": 0, "min_ns": 0, "max_ns": 0, "blocks": []}

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
                dur_ns = max(1.0, b["duration_ns"])
                prod = round(flits / dur_ns, 2)
                role = loc.get("role", "Red")

                b["local_net"] = {
                    "op_type": matched_op["type"],
                    "op_idx": matched_op["idx"],
                    "pkts": pkts,
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

    return {
        "num_gpus": num_gpus,
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


def get_packet_tracking_data(folder_path, offset=0, limit=150, regime="custom"):
    """
    Reads packet_tracking_debug.csv, isolates the steady-state iteration,
    and returns a paginated slice supporting regime presets ('free', 'medium', 'critical', 'custom').
    """
    folder = Path(folder_path).resolve()
    csv_path = folder / "packet_tracking_debug.csv"
    if not csv_path.exists():
        return {
            "has_data": False,
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
            "total_packets": 0,
            "offset": 0,
            "limit": limit,
            "regime": regime,
            "packets": []
        }

    df.columns = df.columns.str.strip()

    # Normalización de columnas
    for col in ["PID", "Source", "Dest", "Creation_Cycle", "Inject_Cycle", "Receive_Cycle",
                "Total_Latency", "Network_Latency", "Queueing_Delay", "Num_Flits", "Size_Bytes",
                "Avg_Flit_Latency", "Throughput", "Op_Idx", "Op_Start_NS", "Op_End_NS"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filtro Anti-Appends para aislar la última iteración
    if "Op_Start_NS" in df.columns and not df["Op_Start_NS"].isna().all():
        drops = df["Op_Start_NS"].diff() < 0
        if drops.any():
            last_reset = drops[drops].index[-1]
            df = df.loc[last_reset:].copy()
    elif "Creation_Cycle" in df.columns:
        drops = df["Creation_Cycle"].diff() < -1000
        if drops.any():
            last_reset = drops[drops].index[-1]
            df = df.loc[last_reset:].copy()

    df = df.dropna(subset=["Creation_Cycle", "Receive_Cycle"]).sort_values(by="PID", ascending=True).reset_index(drop=True)
    total_pkts = len(df)
    if total_pkts == 0:
        return {
            "has_data": False,
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
        # Centrado alrededor de la latencia mediana (P50)
        med_val = df["Total_Latency"].median()
        # Encontrar el índice del paquete más cercano a la mediana
        med_pos = int((df["Total_Latency"] - med_val).abs().values.argmin())
        effective_offset = max(0, med_pos - limit // 2)
    elif regime == "critical":
        # Centrado alrededor del pico máximo de Total_Latency
        max_pos = int(df["Total_Latency"].values.argmax())
        effective_offset = max(0, max_pos - limit // 2)
    else:
        effective_offset = max(0, min(offset, total_pkts - 1))

    # Asegurar límites válidos
    limit = max(10, min(limit, 500))
    df_slice = df.iloc[effective_offset: effective_offset + limit]

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

        # Conversión a tiempo global estimado (1 ciclo = 1 ns)
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
        "total_packets": total_pkts,
        "offset": effective_offset,
        "limit": limit,
        "regime": regime,
        "min_cycle": min_cycle,
        "max_cycle": max_cycle,
        "cycle_span": max_cycle - min_cycle,
        "packets": packets
    }
