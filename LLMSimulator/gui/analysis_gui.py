# -*- coding: utf-8 -*-
"""
Multi-Simulation Analysis and History Engine for LLM-NoC Co-Simulation Workbench.
Scans saved simulations in build/results/ and build/tmp_staging/, extracts metadata,
and generates in-memory comparative figures (Anatomía de Latencia, Desglose MoE,
y Curva de Saturación NoC) along with structured metric tables.
"""

import os
import io
import re
import json
import base64
from pathlib import Path
from datetime import datetime

# Configure headless matplotlib environment
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_tfm")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gui.trace_parser import (
    get_simulation_summary,
    split_dataframe_by_drops,
    get_cluster_iteration_info
)


def _parse_folder_date(folder_name):
    """Extracts timestamp from folder name matching *_YYYYMMDD_HHMMSS."""
    m = re.search(r"(\d{8})_(\d{6})$", folder_name)
    if m:
        d_str, t_str = m.group(1), m.group(2)
        try:
            dt = datetime.strptime(f"{d_str}_{t_str}", "%Y%m%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.timestamp()
        except Exception:
            pass
    return "N/A", 0.0


def list_all_simulations(results_dir, staging_dir=None):
    """
    Scans results_dir (build/results/) and optionally staging_dir (build/tmp_staging/)
    for simulation directories containing *device_*.trc files.
    Returns a list of dicts with lightweight metadata, sorted descending by date.
    Staging (unsaved) simulation appears first if present.
    """
    sims = []
    results_path = Path(results_dir).resolve() if results_dir else None
    staging_path = Path(staging_dir).resolve() if staging_dir else None

    # 1. Check Staging Simulation (Unsaved)
    if staging_path and staging_path.exists():
        for sub in sorted(staging_path.iterdir()):
            if sub.is_dir():
                trc_files = list(sub.glob("*device_*.trc"))
                if trc_files:
                    date_display, ts = _parse_folder_date(sub.name)
                    meta = _extract_lightweight_meta(sub, is_staging=True, date_display=date_display, ts=ts)
                    meta["is_unsaved"] = True
                    meta["source"] = "staging"
                    sims.append(meta)

    # 2. Check Saved Simulations
    if results_path and results_path.exists():
        saved_sims = []
        for sub in sorted(results_path.iterdir()):
            if sub.is_dir():
                trc_files = list(sub.glob("*device_*.trc"))
                if trc_files:
                    date_display, ts = _parse_folder_date(sub.name)
                    meta = _extract_lightweight_meta(sub, is_staging=False, date_display=date_display, ts=ts)
                    meta["is_unsaved"] = False
                    meta["source"] = "saved"
                    saved_sims.append(meta)

        # Sort saved simulations by timestamp descending
        saved_sims.sort(key=lambda x: x.get("timestamp_sort", 0.0), reverse=True)
        sims.extend(saved_sims)

    return sims


def _extract_lightweight_meta(folder_path, is_staging=False, date_display="N/A", ts=0.0):
    """Extracts configuration metadata from config.yaml, test.cfg, gui_metadata.json, or folder name."""
    folder = Path(folder_path)
    name = folder.name
    parts = name.split("_")

    meta = {
        "folder": name,
        "label": "",
        "saved_at": date_display,
        "timestamp_sort": ts,
        "model": "mixtral",
        "topology": "torus",
        "net_dims": "8",
        "num_gpus": 8,
        "vcs": 4,
        "routing": "dim_order",
        "batch_size": 32,
        "tensor_degree": 1,
        "skewness": 0.0,
        "has_packet_csv": (folder / "packet_tracking_debug.csv").exists()
    }

    # Extract model from folder name prefix
    if parts:
        prefix = parts[0].lower()
        if "deepseek" in prefix:
            meta["model"] = "deepseekV3"
        elif "mixtral" in prefix:
            meta["model"] = "mixtral"
        elif "llama" in prefix:
            meta["model"] = "llama"

    # Read gui_metadata.json if available
    gui_meta_file = folder / "gui_metadata.json"
    if gui_meta_file.exists():
        try:
            with open(gui_meta_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if "label" in saved and saved["label"]:
                    meta["label"] = saved["label"]
                if "saved_at" in saved and saved["saved_at"]:
                    meta["saved_at"] = saved["saved_at"]
        except Exception:
            pass

    # Read config.yaml
    cfg_yaml = folder / "config.yaml"
    if cfg_yaml.exists():
        try:
            with open(cfg_yaml, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("model_name:"):
                        meta["model"] = line.split(":", 1)[1].strip()
                    elif line.startswith("num_device:"):
                        meta["num_gpus"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("none_expert_tensor_degree:"):
                        meta["tensor_degree"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("max_batch_size:"):
                        meta["batch_size"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("skewness:"):
                        meta["skewness"] = float(line.split(":", 1)[1].strip())
        except Exception:
            pass

    # Read test.cfg
    test_cfg = folder / "test.cfg"
    if test_cfg.exists():
        try:
            with open(test_cfg, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("topology"):
                        meta["topology"] = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("routing_function"):
                        meta["routing"] = line.split("=")[1].replace(";", "").strip()
                    elif line.startswith("num_vcs"):
                        meta["vcs"] = int(line.split("=")[1].replace(";", "").strip())
        except Exception:
            pass

    # Fallback heuristics from folder name
    for p in parts:
        if p.endswith("dev"):
            meta["net_dims"] = p[:-3]
        elif p.startswith("bs") and p[2:].isdigit():
            meta["batch_size"] = int(p[2:])
        elif p.startswith("tp") and p[2:].isdigit():
            meta["tensor_degree"] = int(p[2:])
        elif p.startswith("skew"):
            try:
                meta["skewness"] = float(p[4:])
            except Exception:
                pass
        elif p in ["torus", "mesh", "ring"]:
            meta["topology"] = p

    return meta


def _extract_op_points(csv_path, num_gpus):
    """Extracts per-operation points (lambda_flits vs lat_flits) from packet_tracking_debug.csv."""
    if not os.path.exists(csv_path):
        return []

    try:
        df = pd.read_csv(csv_path, on_bad_lines="skip")
        if df.empty or "Creation_Cycle" not in df.columns:
            return []

        df.columns = df.columns.str.strip()
        for col in ["Creation_Cycle", "Receive_Cycle", "Num_Flits", "Avg_Flit_Latency", "Total_Latency", "Op_Start_NS"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "Num_Flits" not in df.columns:
            df["Num_Flits"] = 9
        if "Avg_Flit_Latency" not in df.columns:
            df["Avg_Flit_Latency"] = df.get("Total_Latency", 1.0)

        # Anti-appends filter: isolate last iteration
        if "Op_Start_NS" in df.columns and not df["Op_Start_NS"].isna().all():
            drops = df["Op_Start_NS"].diff() < -100.0
            if drops.any():
                last_cut = drops[drops].index[-1]
                df = df.loc[last_cut:].copy()
        elif "Creation_Cycle" in df.columns:
            drops = df["Creation_Cycle"].diff() < -1000.0
            if drops.any():
                last_cut = drops[drops].index[-1]
                df = df.loc[last_cut:].copy()

        df = df.dropna(subset=["Creation_Cycle", "Receive_Cycle"])
        if df.empty:
            return []

        op_points = []
        if "Op_Type" in df.columns and "Op_Idx" in df.columns:
            for (op_t, op_i), grp in df.groupby(["Op_Type", "Op_Idx"]):
                f_cnt = grp["Num_Flits"].sum()
                dur = max(1.0, float(grp["Receive_Cycle"].max() - grp["Creation_Cycle"].min()))
                l_flits = f_cnt / (num_gpus * dur)
                lat_flits = float(grp["Avg_Flit_Latency"].mean())
                op_points.append({
                    "lambda_flits": l_flits,
                    "lat_flits": lat_flits,
                    "op_type": str(op_t),
                    "op_idx": int(op_i) if str(op_i).isdigit() else op_i
                })
        else:
            f_cnt = df["Num_Flits"].sum()
            dur = max(1.0, float(df["Receive_Cycle"].max() - df["Creation_Cycle"].min()))
            l_flits = f_cnt / (num_gpus * dur)
            lat_flits = float(df["Avg_Flit_Latency"].mean())
            op_points.append({
                "lambda_flits": l_flits,
                "lat_flits": lat_flits,
                "op_type": "Colectiva",
                "op_idx": 1
            })

        return op_points
    except Exception as e:
        print(f"⚠️ analysis_gui: Error extrayendo op_points de {csv_path}: {e}")
        return []


def compare_simulations(sim_specs, semilog=False, base_results_dir=None, base_staging_dir=None):
    """
    Receives sim_specs: list of dicts like [{"source": "saved"|"staging", "folder": "<name>"}, ...].
    Extracts metrics and builds:
      - 'rows': list of dicts for tabular presentation and CSV export.
      - 'charts': dict with base64 PNG images for:
          1. anatomia_latencia
          2. desglose_primitivas_moe
          3. curva_saturacion_red (or None if no packet tracking available)
    """
    if not sim_specs:
        return {"rows": [], "charts": {"anatomia_latencia": None, "desglose_primitivas_moe": None, "curva_saturacion_red": None}}

    results_path = Path(base_results_dir).resolve() if base_results_dir else Path("LLMSimulator/build/results").resolve()
    staging_path = Path(base_staging_dir).resolve() if base_staging_dir else Path("LLMSimulator/build/tmp_staging").resolve()

    rows = []
    plot_items = []

    for spec in sim_specs:
        folder_name = spec.get("folder")
        source = spec.get("source", "saved")
        if not folder_name:
            continue

        target_dir = (staging_path / folder_name) if source == "staging" else (results_path / folder_name)
        if not target_dir.exists():
            continue

        try:
            summary = get_simulation_summary(target_dir, iteration="last")
        except Exception as e:
            print(f"⚠️ Error cargando summary de {target_dir}: {e}")
            continue

        wall_clock_us = summary.get("wall_clock_us", 0.0)
        compute_us = summary.get("compute_time_ns", 0.0) / 1000.0
        transit_us = summary.get("network_time_ns", 0.0) / 1000.0
        stall_us = summary.get("stall_time_ns", 0.0) / 1000.0

        scatter_us = summary.get("moe_scatter_ns", 0.0) / 1000.0
        gather_us = summary.get("moe_gather_ns", 0.0) / 1000.0
        allreduce_us = summary.get("all_reduce_ns", 0.0) / 1000.0

        has_csv = summary.get("has_packet_csv", False)
        lambda_flits = summary.get("real_injection_rate_lambda", 0.0)
        flit_lat = summary.get("avg_flit_lat_cycles", 0.0)
        pkt_lat = summary.get("avg_pkt_lat_cycles", 0.0)

        # Human readable display label
        custom_label = summary.get("label", "").strip()
        display_label = custom_label if custom_label else folder_name
        model_name = summary.get("model", "mixtral")
        topo = summary.get("topology", "torus")
        gpus = summary.get("num_gpus", 8)
        bs = summary.get("batch_size", 32)
        vcs = summary.get("vcs", 4)
        tp = summary.get("tensor_degree", 1)
        skew = summary.get("skewness", 0.0)

        tp_str = f", TP={tp}" if tp > 1 else ""
        skew_str = f", Skew={skew}" if skew > 0.0 else ""
        compact_label = f"{model_name} {gpus}dev {topo.capitalize()} (BS={bs}{tp_str}{skew_str})"
        if custom_label:
            compact_label = f"{custom_label}\n[{compact_label}]"

        row = {
            "folder": folder_name,
            "label": custom_label if custom_label else folder_name,
            "display_label": compact_label,
            "source": source,
            "is_unsaved": source == "staging",
            "model": model_name,
            "topology": topo,
            "net_dims": summary.get("net_dims", str(gpus)),
            "num_gpus": gpus,
            "vcs": vcs,
            "batch_size": bs,
            "tp": tp,
            "skewness": skew,
            "wall_clock_us": round(wall_clock_us, 2),
            "compute_us": round(compute_us, 2),
            "compute_pct": round(summary.get("compute_pct", 0.0), 1),
            "transit_us": round(transit_us, 2),
            "transit_pct": round(summary.get("network_pct", 0.0), 1),
            "stall_us": round(stall_us, 2),
            "stall_pct": round(summary.get("stall_pct", 0.0), 1),
            "scatter_us": round(scatter_us, 2),
            "gather_us": round(gather_us, 2),
            "allreduce_us": round(allreduce_us, 2),
            "has_packet_csv": has_csv,
            "lambda_flits": round(lambda_flits, 4),
            "avg_flit_lat_cycles": round(flit_lat, 2),
            "avg_pkt_lat_cycles": round(pkt_lat, 2),
            "total_packets": summary.get("total_packets", 0),
            "total_flits": summary.get("total_flits", 0)
        }
        rows.append(row)

        # Extract op_points for network saturation curve
        op_points = []
        if has_csv:
            csv_file = target_dir / "packet_tracking_debug.csv"
            op_points = _extract_op_points(str(csv_file), gpus)

        plot_items.append({
            "folder": folder_name,
            "label": compact_label,
            "short_label": custom_label if custom_label else folder_name[:26],
            "compute_us": compute_us,
            "transit_us": transit_us,
            "stall_us": stall_us,
            "total_us": compute_us + transit_us + stall_us,
            "wall_clock_us": wall_clock_us,
            "scatter_us": scatter_us,
            "gather_us": gather_us,
            "allreduce_us": allreduce_us,
            "has_csv": has_csv,
            "lambda_flits": lambda_flits,
            "avg_flit_lat": flit_lat,
            "op_points": op_points
        })

    if not rows:
        return {"rows": [], "charts": {"anatomia_latencia": None, "desglose_primitivas_moe": None, "curva_saturacion_red": None}}

    # -------------------------------------------------------------------------
    # Generate Charts
    # -------------------------------------------------------------------------
    chart_anatomia = _plot_anatomia_latencia(plot_items)
    chart_primitivas = _plot_desglose_primitivas(plot_items)
    chart_saturacion = _plot_curva_saturacion(plot_items, force_semilog=semilog)

    return {
        "rows": rows,
        "charts": {
            "anatomia_latencia": chart_anatomia,
            "desglose_primitivas_moe": chart_primitivas,
            "curva_saturacion_red": chart_saturacion
        }
    }


def _fig_to_base64(fig):
    """Renders a matplotlib figure to a base64 PNG data URI string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _plot_anatomia_latencia(items):
    """Chart 1: Stacked bar chart of Compute, Network Transit, and Synchronization Stalls."""
    fig, ax = plt.subplots(figsize=(max(8.5, len(items) * 2.2), 6.5))

    indices = np.arange(len(items))
    bar_width = 0.52

    compute_vals = [it["compute_us"] for it in items]
    transit_vals = [it["transit_us"] for it in items]
    stall_vals = [it["stall_us"] for it in items]

    # Stacked bars
    p1 = ax.bar(indices, compute_vals, bar_width, color="#10b981", label="Cómputo GPU (Attn/FFN)", edgecolor="#059669", linewidth=1)
    p2 = ax.bar(indices, transit_vals, bar_width, bottom=compute_vals, color="#38bdf8", label="Tránsito NoC (BookSim2)", edgecolor="#0284c7", linewidth=1)
    p3 = ax.bar(indices, stall_vals, bar_width, bottom=[c + t for c, t in zip(compute_vals, transit_vals)],
                color="#ef4444", label="Stalls de Barrera (BSP)", edgecolor="#b91c1c", linewidth=1)

    ax.set_title("TFM: Anatomía de Latencia por Dispositivo (Cómputo vs. Red vs. Stalls)", fontsize=13, fontweight="bold", pad=14)
    ax.set_ylabel("Tiempo de Ejecución Promedio (µs)", fontsize=11, fontweight="semibold")
    ax.set_xticks(indices)
    ax.set_xticklabels([it["short_label"] for it in items], rotation=15, ha="right", fontsize=9.5)
    ax.legend(fontsize=9.5, loc="upper left", framealpha=0.92, edgecolor="#cccccc")
    ax.grid(axis="y", linestyle="--", alpha=0.55, color="#888888")

    # Annotations on top of each stacked bar
    for idx, it in enumerate(items):
        total_val = it["total_us"]
        wall_val = it["wall_clock_us"]
        ms_str = f"({total_val / 1000.0:.3f} ms)" if total_val >= 1000.0 else ""
        badge_text = f"{total_val:,.1f} µs\n{ms_str}".strip()

        ax.annotate(
            badge_text,
            xy=(idx, total_val),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=8.5, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#94a3b8", alpha=0.92, lw=1)
        )

    max_val = max(it["total_us"] for it in items) if items else 100.0
    ax.set_ylim(0, max_val * 1.25)
    fig.tight_layout()

    return _fig_to_base64(fig)


def _plot_desglose_primitivas(items):
    """Chart 2: Grouped bar chart comparing MoE Scatter, MoE Gather, and AllReduce."""
    fig, ax = plt.subplots(figsize=(max(8.5, len(items) * 2.2), 6.5))

    has_allreduce = any(it["allreduce_us"] > 0.05 for it in items)
    num_bars = 3 if has_allreduce else 2

    bar_width = 0.26 if has_allreduce else 0.35
    indices = np.arange(len(items))

    scatter_vals = [it["scatter_us"] for it in items]
    gather_vals = [it["gather_us"] for it in items]
    allreduce_vals = [it["allreduce_us"] for it in items]

    if has_allreduce:
        ax.bar(indices - bar_width, scatter_vals, bar_width, color="#38bdf8", label="MoE Scatter (Tokens a Expertos)", edgecolor="#0284c7", linewidth=1)
        ax.bar(indices, gather_vals, bar_width, color="#2563eb", label="MoE Gather (Recolección de Resultados)", edgecolor="#1d4ed8", linewidth=1)
        ax.bar(indices + bar_width, allreduce_vals, bar_width, color="#a855f7", label="Ring-AllReduce (Capas Densas)", edgecolor="#7e22ce", linewidth=1)
    else:
        ax.bar(indices - bar_width / 2, scatter_vals, bar_width, color="#38bdf8", label="MoE Scatter (Tokens a Expertos)", edgecolor="#0284c7", linewidth=1)
        ax.bar(indices + bar_width / 2, gather_vals, bar_width, color="#2563eb", label="MoE Gather (Recolección de Resultados)", edgecolor="#1d4ed8", linewidth=1)

    ax.set_title("TFM: Coste de las Primitivas de Red Colectivas (Scatter vs. Gather vs. AllReduce)", fontsize=13, fontweight="bold", pad=14)
    ax.set_ylabel("Tiempo Medio por Dispositivo (µs)", fontsize=11, fontweight="semibold")
    ax.set_xticks(indices)
    ax.set_xticklabels([it["short_label"] for it in items], rotation=15, ha="right", fontsize=9.5)
    ax.legend(fontsize=9.5, loc="upper left", framealpha=0.92, edgecolor="#cccccc")
    ax.grid(axis="y", linestyle="--", alpha=0.55, color="#888888")

    max_moe = max(max(scatter_vals), max(gather_vals), max(allreduce_vals) if has_allreduce else 0.0)
    ax.set_ylim(0, max_moe * 1.25 if max_moe > 0 else 10.0)
    fig.tight_layout()

    return _fig_to_base64(fig)


def _plot_curva_saturacion(items, force_semilog=False):
    """Chart 3: Network Saturation Curve (Lambda vs. Average Flit Latency) with scatter cloud & centroids."""
    net_items = [it for it in items if it.get("has_csv") and it.get("lambda_flits", 0.0) > 0]
    if not net_items:
        return None

    fig, ax = plt.subplots(figsize=(10.5, 7.0))
    palette = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e", "#17becf", "#e377c2", "#8c564b"]
    markers = ["o", "s", "^", "D", "v", "p", "*", "h"]

    all_lats = [pt["lat_flits"] for it in net_items for pt in it.get("op_points", [])]
    lat_min = min(all_lats) if all_lats else min(it["avg_flit_lat"] for it in net_items)
    lat_max = max(all_lats) if all_lats else max(it["avg_flit_lat"] for it in net_items)

    use_semilog = force_semilog or ((lat_max / max(1.0, lat_min) >= 4.0) and (lat_max - lat_min > 500))

    # Sort by injection rate for saturation trend line
    sorted_items = sorted(net_items, key=lambda x: x["lambda_flits"])

    for idx, it in enumerate(net_items):
        col = palette[idx % len(palette)]
        mk = markers[idx % len(markers)]
        l_mean = it["lambda_flits"]
        lat_mean = it["avg_flit_lat"]
        tag = it["short_label"]

        # Translucent scatter cloud of individual ops
        op_points = it.get("op_points", [])
        if op_points:
            xs_ops = [p["lambda_flits"] for p in op_points]
            ys_ops = [p["lat_flits"] for p in op_points]
            ax.scatter(xs_ops, ys_ops, color=col, alpha=0.22, s=36, edgecolors="none", zorder=2)

        # Highlighted geometric centroid
        ax.scatter(l_mean, lat_mean, color=col, marker=mk, s=220,
                   edgecolors="black", linewidths=1.8, zorder=5,
                   label=f"{tag} (λ={l_mean:.4f}, Lat={lat_mean:.1f}c)")

        # Annotated badge with arrow
        ax.annotate(
            f"{tag}\nλ={l_mean:.4f} f/c/nodo\nLat={lat_mean:.1f} ciclos",
            xy=(l_mean, lat_mean),
            xytext=(14, 12),
            textcoords="offset points",
            fontsize=8.5, fontweight="semibold",
            bbox=dict(boxstyle="round,pad=0.32", fc="white", ec=col, alpha=0.92, lw=1.2),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.15", color=col, lw=1.2),
            zorder=6
        )

    # Dashed trend line
    if len(sorted_items) >= 2:
        xs_trend = [it["lambda_flits"] for it in sorted_items]
        ys_trend = [it["avg_flit_lat"] for it in sorted_items]
        ax.plot(xs_trend, ys_trend, linestyle="--", color="#555555", alpha=0.55, linewidth=1.5, zorder=3, label="Tendencia de Saturación")

    if use_semilog:
        ax.set_yscale("log")
        ax.set_ylabel("Latencia Media de Flit [ciclos BookSim2] (Escala Logarítmica)", fontsize=11, fontweight="semibold")
    else:
        ax.set_ylabel("Latencia Media de Flit [ciclos BookSim2]", fontsize=11, fontweight="semibold")
        ax.set_ylim(bottom=0)

    ax.set_xlabel(r"Tasa Media de Inyección Real $\lambda$ [flits / ciclo / nodo]", fontsize=11, fontweight="semibold")
    ax.set_title("TFM: Curva de Saturación de Red NoC (Latencia vs. Carga Inyectada)", fontsize=13, fontweight="bold", pad=14)
    ax.grid(True, which="both", linestyle=":", alpha=0.55, color="#888888", zorder=1)
    ax.legend(fontsize=9.0, loc="upper left", framealpha=0.92, edgecolor="#cccccc")

    fig.tight_layout()
    return _fig_to_base64(fig)

