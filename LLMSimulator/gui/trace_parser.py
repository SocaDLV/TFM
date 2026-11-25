# -*- coding: utf-8 -*-
"""
Trace and Packet Tracking Parser for LLM-NoC Co-Simulation Workbench.
Reconstructs cycle-to-cycle GPU chronograms, packet flight data, macroscopic KPIs,
and synchronized hybrid split-screen projections directly from raw files
(.trc and packet_tracking_debug.csv) without generating static PNGs.
Supports multi-iteration analysis (Iteración 1..N o Simulación Completa).
"""

import os
import gc
import glob
import re
import json
import threading
from contextlib import nullcontext
from collections import OrderedDict
import numpy as np
import pandas as pd
from pathlib import Path


SAFE_MAX_PACKETS = 2500

_PATH_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS = {}

_CSV_CACHE_LOCK = threading.Lock()
_CSV_CACHE = OrderedDict()
_CSV_CACHE_MAX_ENTRIES = 2
_CSV_CACHE_MAX_BYTES = 450 * 1024 * 1024

_TRC_CACHE_LOCK = threading.Lock()
_TRC_CACHE = OrderedDict()
_TRC_CACHE_MAX_ENTRIES = 48

_CLUSTER_INFO_CACHE_LOCK = threading.Lock()
_CLUSTER_INFO_CACHE = OrderedDict()
_CLUSTER_INFO_CACHE_MAX = 8

_RESULT_CACHE_LOCK = threading.Lock()
_SUMMARY_CACHE = OrderedDict()   # (resolved_folder, iteration) -> {"sig": ..., "data": ...}
_CHRONO_CACHE = OrderedDict()    # (resolved_folder, iteration) -> {"sig": ..., "data": ...}
_RESULT_CACHE_MAX = 2

_HEAVY_DF_OP_LOCK = threading.Lock()


def _get_path_lock(resolved_path):
    """Returns a dedicated threading.Lock per canonical file path."""
    key = str(resolved_path)
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[key] = lock
        return lock


def _malloc_trim():
    """Asks glibc to return freed heap arenas back to the OS."""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def invalidate_simulation_cache(folder_path=None):
    """
    Evicts cached CSV, TRC, summary, chronogram, and iteration metadata entries
    for folder_path (or clears all caches if folder_path is None) and triggers gc.collect().
    """
    target_prefix = str(Path(folder_path).resolve()) if folder_path else None
    with _CSV_CACHE_LOCK:
        if target_prefix is None:
            _CSV_CACHE.clear()
        else:
            for k in [k for k in _CSV_CACHE if k == target_prefix or k.startswith(target_prefix + os.sep)]:
                del _CSV_CACHE[k]

    with _TRC_CACHE_LOCK:
        if target_prefix is None:
            _TRC_CACHE.clear()
        else:
            for k in [k for k in _TRC_CACHE if k == target_prefix or k.startswith(target_prefix + os.sep)]:
                del _TRC_CACHE[k]

    with _CLUSTER_INFO_CACHE_LOCK:
        if target_prefix is None:
            _CLUSTER_INFO_CACHE.clear()
        else:
            _CLUSTER_INFO_CACHE.pop(target_prefix, None)

    with _RESULT_CACHE_LOCK:
        if target_prefix is None:
            _SUMMARY_CACHE.clear()
            _CHRONO_CACHE.clear()
        else:
            for cache_d in (_SUMMARY_CACHE, _CHRONO_CACHE):
                for k in [k for k in cache_d if k[0] == target_prefix]:
                    del cache_d[k]

    gc.collect()
    _malloc_trim()


def _compute_drop_bounds(df, col_name, drop_threshold=-1.0):
    """
    Computes contiguous iteration index ranges [(start, end), ...] whenever col_name drops
    by more than drop_threshold, using zero-copy NumPy operations.
    """
    n = len(df)
    if n == 0 or col_name not in df.columns:
        return [(0, n)] if n > 0 else []

    vals = df[col_name].to_numpy(dtype=np.float64, copy=False)
    if len(vals) <= 1:
        return [(0, n)]

    drop_pos = np.flatnonzero(np.diff(vals) < drop_threshold) + 1
    if len(drop_pos) == 0:
        return [(0, n)]

    cuts = [0] + drop_pos.tolist() + [n]
    bounds = []
    for i in range(len(cuts) - 1):
        if cuts[i + 1] > cuts[i]:
            bounds.append((cuts[i], cuts[i + 1]))
    return bounds if bounds else [(0, n)]


def split_dataframe_by_drops(df, col_name, drop_threshold=-1.0):
    """
    Splits a DataFrame into sequential iteration slice views whenever col_name drops
    by more than drop_threshold (e.g. START_NS < -1.0 or Op_Start_NS < -100.0).
    Returns a list of DataFrame views without unnecessary full-frame copies.
    """
    if df.empty or col_name not in df.columns:
        return [df]
    bounds = _compute_drop_bounds(df, col_name, drop_threshold)
    if len(bounds) == 1 and bounds[0] == (0, len(df)):
        return [df]
    return [df.iloc[s:e] for (s, e) in bounds]


def _load_trc_cached(trc_path):
    """
    Thread-safe cached loader for a single *device_*.trc file.
    Validates (mtime_ns, size) and returns immutable (df, seg_bounds).
    """
    resolved = str(Path(trc_path).resolve())
    st = os.stat(resolved)
    sig = (st.st_mtime_ns, st.st_size)

    with _TRC_CACHE_LOCK:
        entry = _TRC_CACHE.get(resolved)
        if entry is not None and entry["sig"] == sig:
            _TRC_CACHE.move_to_end(resolved)
            return entry["df"], entry["seg_bounds"]

    path_lock = _get_path_lock(resolved)
    with path_lock:
        with _TRC_CACHE_LOCK:
            entry = _TRC_CACHE.get(resolved)
            if entry is not None and entry["sig"] == sig:
                _TRC_CACHE.move_to_end(resolved)
                return entry["df"], entry["seg_bounds"]

        df = pd.read_csv(resolved, on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        df["START_NS"] = pd.to_numeric(df["START_NS"], errors="coerce")
        df["END_NS"] = pd.to_numeric(df["END_NS"], errors="coerce")
        df["DURATION"] = pd.to_numeric(df["DURATION"], errors="coerce")
        df = df.dropna(subset=["START_NS", "END_NS", "DURATION"])
        df = df[df["DURATION"] > 0].reset_index(drop=True)
        if "TYPE" in df.columns:
            df["TYPE"] = df["TYPE"].astype(str).str.strip()
        if "DETAILS" in df.columns:
            df["DETAILS"] = df["DETAILS"].fillna("").astype(str).str.strip()
        else:
            df["DETAILS"] = ""

        seg_bounds = _compute_drop_bounds(df, "START_NS", -1.0)

        with _TRC_CACHE_LOCK:
            _TRC_CACHE[resolved] = {"sig": sig, "df": df, "seg_bounds": seg_bounds}
            _TRC_CACHE.move_to_end(resolved)
            while len(_TRC_CACHE) > _TRC_CACHE_MAX_ENTRIES:
                _TRC_CACHE.popitem(last=False)

        return df, seg_bounds


def load_packet_csv_cached(folder_path):
    """
    Thread-safe LRU cached loader for packet_tracking_debug.csv.
    Uses compact dtypes (int32/int16/float32/category) and minimal usecols to keep
    ~9.2M rows under ~350 MB RAM, synchronized by per-file threading.Lock.
    Returns (df, seg_bounds) or (None, []) if missing/empty.
    """
    folder = Path(folder_path).resolve()
    csv_path = folder / "packet_tracking_debug.csv"
    if not csv_path.exists():
        return None, []

    resolved = str(csv_path)
    st = os.stat(resolved)
    sig = (st.st_mtime_ns, st.st_size)

    with _CSV_CACHE_LOCK:
        entry = _CSV_CACHE.get(resolved)
        if entry is not None and entry["sig"] == sig:
            _CSV_CACHE.move_to_end(resolved)
            return entry["df"], entry["seg_bounds"]

    path_lock = _get_path_lock(resolved)
    with path_lock:
        with _CSV_CACHE_LOCK:
            entry = _CSV_CACHE.get(resolved)
            if entry is not None and entry["sig"] == sig:
                _CSV_CACHE.move_to_end(resolved)
                return entry["df"], entry["seg_bounds"]

        # If loading a large CSV (>120 MB on disk), evict other cached CSVs first to bound peak RSS
        if st.st_size > 120 * 1024 * 1024:
            evicted = False
            with _CSV_CACHE_LOCK:
                for k in list(_CSV_CACHE.keys()):
                    if k != resolved:
                        del _CSV_CACHE[k]
                        evicted = True
            if evicted:
                gc.collect()

        with open(resolved, "r", encoding="utf-8", errors="ignore") as fh:
            header_line = fh.readline()
        if not header_line:
            return None, []

        raw_cols = [c for c in header_line.rstrip("\r\n").split(",")]
        stripped_to_raw = {c.strip(): c for c in raw_cols if c.strip()}

        essential_cols = [
            "PID", "Source", "Dest",
            "Creation_Cycle", "Inject_Cycle", "Receive_Cycle",
            "Num_Flits", "Avg_Flit_Latency",
            "Op_Type", "Op_Idx", "Op_Start_NS",
        ]
        # Only load legacy latency columns if raw cycle columns are absent
        has_all_cycles = all(c in stripped_to_raw for c in ("Creation_Cycle", "Inject_Cycle", "Receive_Cycle"))
        if not has_all_cycles:
            essential_cols.extend(["Total_Latency", "Latency", "Network_Latency", "Queueing_Delay"])

        usecols_raw = [stripped_to_raw[c] for c in essential_cols if c in stripped_to_raw]
        if not usecols_raw:
            return None, []

        compact_dtypes = {
            "PID": "int32",
            "Source": "int16",
            "Dest": "int16",
            "Creation_Cycle": "int32",
            "Inject_Cycle": "int32",
            "Receive_Cycle": "int32",
            "Total_Latency": "int32",
            "Latency": "int32",
            "Network_Latency": "int32",
            "Queueing_Delay": "int32",
            "Num_Flits": "int16",
            "Avg_Flit_Latency": "float32",
            "Op_Type": "category",
            "Op_Idx": "int16",
            "Op_Start_NS": "float64",
        }
        dtypes_raw = {
            stripped_to_raw[k]: v
            for k, v in compact_dtypes.items()
            if k in stripped_to_raw and stripped_to_raw[k] in usecols_raw
        }

        df = None
        try:
            if st.st_size > 40 * 1024 * 1024:
                # Pre-allocated chunked path for huge CSVs: cuts peak RSS from ~720 MB to ~435 MB
                n_lines = 0
                last_byte = b"\n"
                with open(resolved, "rb") as bf:
                    while True:
                        buf = bf.read(4 * 1024 * 1024)
                        if not buf:
                            break
                        n_lines += buf.count(b"\n")
                        last_byte = buf[-1:]
                if last_byte != b"\n":
                    n_lines += 1
                n_rows = max(0, n_lines - 1)

                if n_rows > 0:
                    np_dtype_map = {
                        "int32": np.int32,
                        "int16": np.int16,
                        "float32": np.float32,
                        "float64": np.float64,
                    }
                    arrs = {}
                    chunk_dtypes = {}
                    has_op_type = False
                    for raw_c in usecols_raw:
                        norm_c = raw_c.strip()
                        dt_str = compact_dtypes.get(norm_c, "float32")
                        chunk_dtypes[raw_c] = dt_str
                        if norm_c == "Op_Type" and dt_str == "category":
                            has_op_type = True
                            arrs["_op_codes"] = np.empty(n_rows, dtype=np.int16)
                        else:
                            arrs[norm_c] = np.empty(n_rows, dtype=np_dtype_map.get(dt_str, np.float32))

                    cat_list = []
                    cat_map = {}
                    pos = 0
                    for ch in pd.read_csv(
                        resolved,
                        usecols=usecols_raw,
                        dtype=chunk_dtypes,
                        chunksize=250_000,
                        na_filter=False,
                        on_bad_lines="skip",
                    ):
                        k = len(ch)
                        if k == 0:
                            continue
                        if pos + k > n_rows:
                            # Defensive grow in case line estimate was low
                            extra = (pos + k) - n_rows
                            n_rows += extra
                            for ak in arrs:
                                arrs[ak] = np.resize(arrs[ak], n_rows)
                        for raw_c in usecols_raw:
                            norm_c = raw_c.strip()
                            if norm_c == "Op_Type" and has_op_type:
                                ch_codes = ch[raw_c].cat.codes.to_numpy(dtype=np.int16, copy=False)
                                cats = ch[raw_c].cat.categories.tolist()
                                lookup = np.empty(len(cats), dtype=np.int16)
                                for ci, cname in enumerate(cats):
                                    cid = cat_map.get(cname)
                                    if cid is None:
                                        cid = len(cat_list)
                                        cat_map[cname] = cid
                                        cat_list.append(cname)
                                    lookup[ci] = cid
                                arrs["_op_codes"][pos : pos + k] = lookup[ch_codes]
                            else:
                                arrs[norm_c][pos : pos + k] = ch[raw_c].to_numpy(copy=False)
                        pos += k

                    op_cat = None
                    if has_op_type:
                        codes_final = arrs.pop("_op_codes")[:pos]
                        op_cat = pd.Categorical.from_codes(codes_final, categories=cat_list)
                    df = pd.DataFrame(
                        {col_n: (v[:pos] if pos < n_rows else v) for col_n, v in arrs.items()},
                        copy=False,
                    )
                    if op_cat is not None:
                        df["Op_Type"] = op_cat
                    del arrs
            else:
                df = pd.read_csv(
                    resolved,
                    usecols=usecols_raw,
                    dtype=dtypes_raw,
                    na_filter=False,
                    on_bad_lines="skip",
                )
                df.columns = df.columns.str.strip()
        except Exception:
            # Fallback for legacy/malformed CSVs containing NaNs or float cycles
            df = pd.read_csv(resolved, usecols=usecols_raw, on_bad_lines="skip")
            df.columns = df.columns.str.strip()
            for col in ["PID", "Source", "Dest", "Creation_Cycle", "Inject_Cycle", "Receive_Cycle",
                        "Total_Latency", "Latency", "Network_Latency", "Queueing_Delay", "Num_Flits", "Op_Idx"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "Op_Start_NS" in df.columns:
                df["Op_Start_NS"] = pd.to_numeric(df["Op_Start_NS"], errors="coerce")
            if "Avg_Flit_Latency" in df.columns:
                df["Avg_Flit_Latency"] = pd.to_numeric(df["Avg_Flit_Latency"], errors="coerce").astype("float32")
            req_drop = [c for c in ("Creation_Cycle", "Receive_Cycle") if c in df.columns]
            if req_drop:
                df = df.dropna(subset=req_drop).reset_index(drop=True)
            for col, target_dt in compact_dtypes.items():
                if col in df.columns:
                    if target_dt == "category":
                        df[col] = df[col].astype("category")
                    elif target_dt in ("int16", "int32"):
                        vals = df[col].fillna(0)
                        if target_dt == "int16" and vals.abs().max() < 32767:
                            df[col] = vals.astype("int16")
                        elif vals.abs().max() < 2147483647:
                            df[col] = vals.astype("int32")

        if df is None or df.empty:
            return None, []

        # Synthesize Creation_Cycle / Receive_Cycle for very old legacy CSVs if needed
        if "Creation_Cycle" not in df.columns and "Inject_Cycle" in df.columns:
            df["Creation_Cycle"] = df["Inject_Cycle"]
        if "Receive_Cycle" not in df.columns and "Creation_Cycle" in df.columns:
            lat_col = "Total_Latency" if "Total_Latency" in df.columns else ("Latency" if "Latency" in df.columns else None)
            if lat_col is not None:
                df["Receive_Cycle"] = df["Creation_Cycle"] + df[lat_col]

        seg_bounds = _compute_drop_bounds(df, "Op_Start_NS", -100.0)
        mem_bytes = int(df.memory_usage(deep=True).sum())

        with _CSV_CACHE_LOCK:
            _CSV_CACHE[resolved] = {
                "sig": sig,
                "df": df,
                "seg_bounds": seg_bounds,
                "mem_bytes": mem_bytes,
            }
            _CSV_CACHE.move_to_end(resolved)

            total_bytes = sum(v["mem_bytes"] for v in _CSV_CACHE.values())
            while len(_CSV_CACHE) > _CSV_CACHE_MAX_ENTRIES or (total_bytes > _CSV_CACHE_MAX_BYTES and len(_CSV_CACHE) > 1):
                _, popped = _CSV_CACHE.popitem(last=False)
                total_bytes -= popped["mem_bytes"]

        if mem_bytes > 50 * 1024 * 1024:
            gc.collect()
            _malloc_trim()

        return df, seg_bounds


def get_cluster_iteration_info(folder_path):
    """
    Scans all *device_*.trc files in folder_path (via _TRC_CACHE) to determine
    the number of iterations and the max wall-clock duration of each iteration across all GPUs.
    Returns: (num_iters, durations_list, offsets_list)
    """
    folder = Path(folder_path).resolve()
    trc_files = sorted(glob.glob(str(folder / "*device_*.trc")))
    if not trc_files:
        return 1, [0.0], [0.0]

    folder_key = str(folder)
    try:
        sig = tuple((tf, os.stat(tf).st_mtime_ns, os.stat(tf).st_size) for tf in trc_files)
    except OSError:
        sig = None

    if sig is not None:
        with _CLUSTER_INFO_CACHE_LOCK:
            cached = _CLUSTER_INFO_CACHE.get(folder_key)
            if cached is not None and cached["sig"] == sig:
                _CLUSTER_INFO_CACHE.move_to_end(folder_key)
                return cached["info"]

    max_ends_per_iter = {}
    min_starts_per_iter = {}

    for tf in trc_files:
        try:
            df, seg_bounds = _load_trc_cached(tf)
            if df.empty:
                continue

            starts_arr = df["START_NS"].to_numpy(dtype=np.float64, copy=False)
            ends_arr = df["END_NS"].to_numpy(dtype=np.float64, copy=False)
            for k, (s_idx, e_idx) in enumerate(seg_bounds):
                if e_idx <= s_idx:
                    continue
                s_min = float(starts_arr[s_idx:e_idx].min())
                e_max = float(ends_arr[s_idx:e_idx].max())
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

    result = (num_iters, durations, offsets)
    if sig is not None:
        with _CLUSTER_INFO_CACHE_LOCK:
            _CLUSTER_INFO_CACHE[folder_key] = {"sig": sig, "info": result}
            _CLUSTER_INFO_CACHE.move_to_end(folder_key)
            while len(_CLUSTER_INFO_CACHE) > _CLUSTER_INFO_CACHE_MAX:
                _CLUSTER_INFO_CACHE.popitem(last=False)

    return result


def load_network_ops_debug(folder_path, iteration="last", iteration_offsets=None):
    """
    Loads packet_tracking_debug.csv via thread-safe cache, selects iteration slices without
    copying the full DataFrame, and aggregates per-collective and per-GPU stats vectorially.
    """
    try:
        df_p, seg_bounds = load_packet_csv_cached(folder_path)
        if df_p is None or df_p.empty or "Op_Type" not in df_p.columns:
            return []

        num_iters = len(seg_bounds)
        if num_iters == 0:
            return []

        if iteration == "all":
            slices_to_process = [
                (k + 1, df_p.iloc[s:e], iteration_offsets[k] if (iteration_offsets and k < len(iteration_offsets)) else 0.0)
                for k, (s, e) in enumerate(seg_bounds)
            ]
        elif iteration == "last":
            s, e = seg_bounds[-1]
            slices_to_process = [(num_iters, df_p.iloc[s:e], 0.0)]
        else:
            try:
                iter_k = int(iteration) - 1
                idx = iter_k if 0 <= iter_k < num_iters else num_iters - 1
            except ValueError:
                idx = num_iters - 1
            s, e = seg_bounds[idx]
            slices_to_process = [(idx + 1, df_p.iloc[s:e], 0.0)]

        max_src = int(df_p["Source"].max()) if "Source" in df_p.columns and not df_p.empty else 7
        max_dst = int(df_p["Dest"].max()) if "Dest" in df_p.columns and not df_p.empty else 7
        num_gpus = max(8, max(max_src, max_dst) + 1)

        ops = []
        for iter_num, seg_view, off_ns in slices_to_process:
            if seg_view.empty:
                continue

            has_flits = "Num_Flits" in seg_view.columns
            has_avg_flit = "Avg_Flit_Latency" in seg_view.columns
            has_op_start = "Op_Start_NS" in seg_view.columns
            has_rx = "Receive_Cycle" in seg_view.columns
            has_cr = "Creation_Cycle" in seg_view.columns

            op_agg_dict = {
                "min_pid": ("PID", "min"),
                "max_pid": ("PID", "max"),
                "total_pkts": ("PID", "count"),
            }
            if has_op_start:
                op_agg_dict["start_ns"] = ("Op_Start_NS", "first")
            if has_rx:
                op_agg_dict["max_rx"] = ("Receive_Cycle", "max")
            if has_avg_flit:
                op_agg_dict["avg_flit_lat"] = ("Avg_Flit_Latency", "last")

            op_summary = seg_view.groupby(["Op_Type", "Op_Idx"], observed=True, sort=False).agg(**op_agg_dict)

            # Vectorized per-GPU TX (Source) & RX (Dest) aggregations
            gpu_agg_cols = {
                "pkts": ("PID", "count"),
                "min_pid": ("PID", "min"),
                "max_pid": ("PID", "max"),
            }
            if has_flits:
                gpu_agg_cols["flits"] = ("Num_Flits", "sum")
            if has_rx and has_cr:
                gpu_agg_cols["sum_rx"] = ("Receive_Cycle", "sum")
                gpu_agg_cols["sum_cr"] = ("Creation_Cycle", "sum")
            elif "Total_Latency" in seg_view.columns:
                gpu_agg_cols["sum_lat"] = ("Total_Latency", "sum")

            tx_agg = seg_view.groupby(["Op_Type", "Op_Idx", "Source"], observed=True, sort=False).agg(**gpu_agg_cols)
            rx_agg = seg_view.groupby(["Op_Type", "Op_Idx", "Dest"], observed=True, sort=False).agg(**gpu_agg_cols)

            tx_lookup = tx_agg.to_dict("index")
            rx_lookup = rx_agg.to_dict("index")

            for (op_type, op_idx), row in op_summary.iterrows():
                start_ns = float(row["start_ns"]) + off_ns if "start_ns" in row else off_ns
                max_rx_val = float(row["max_rx"]) if "max_rx" in row else 0.0
                end_ns = start_ns + max_rx_val + 1.0
                min_pid = int(row["min_pid"])
                max_pid = int(row["max_pid"])
                total_pkts = int(row["total_pkts"])
                final_avg_lat = float(row["avg_flit_lat"]) if "avg_flit_lat" in row else 0.0

                op_type_lower = str(op_type).lower()
                gpu_data = {}
                for d in range(num_gpus):
                    if "scatter" in op_type_lower:
                        rec = rx_lookup.get((op_type, op_idx, d))
                        role = "RX (Experto Destino)"
                    elif "gather" in op_type_lower:
                        rec = tx_lookup.get((op_type, op_idx, d))
                        role = "TX (Activación Origen)"
                    elif "allreduce" in op_type_lower or "all_reduce" in op_type_lower:
                        rec = rx_lookup.get((op_type, op_idx, d)) or tx_lookup.get((op_type, op_idx, d))
                        role = "Ring TP"
                    else:
                        rec = rx_lookup.get((op_type, op_idx, d)) or tx_lookup.get((op_type, op_idx, d))
                        role = "P2P"

                    if rec and rec["pkts"] > 0:
                        n_local = int(rec["pkts"])
                        if "sum_rx" in rec and "sum_cr" in rec:
                            lat_local = float(rec["sum_rx"] - rec["sum_cr"]) / n_local
                        elif "sum_lat" in rec:
                            lat_local = float(rec["sum_lat"]) / n_local
                        else:
                            lat_local = 0.0
                        flits_local = int(rec["flits"]) if "flits" in rec else n_local * 9
                        min_pid_local = int(rec["min_pid"])
                        max_pid_local = int(rec["max_pid"])
                    else:
                        n_local = 0
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
                        "role": role,
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
                    "throughput": 0.0,
                    "gpu_data": gpu_data,
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

    cache_key = (str(folder), str(iteration))
    sig = _get_folder_sig(folder)
    if sig is not None:
        with _RESULT_CACHE_LOCK:
            cached = _SUMMARY_CACHE.get(cache_key)
            if cached is not None and cached["sig"] == sig:
                _SUMMARY_CACHE.move_to_end(cache_key)
                return cached["data"]

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

    # 2. Análisis multi-iteración de los archivos .trc (mediante caché thread-safe)
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
            df, seg_bounds = _load_trc_cached(trc_path)
            if df.empty or not seg_bounds:
                continue

            if target_iter_mode == "all":
                df_active = df
            else:
                idx = min(target_iter_mode, len(seg_bounds) - 1)
                s_b, e_b = seg_bounds[idx]
                df_active = df.iloc[s_b:e_b]

            type_lower = df_active["TYPE"].str.lower()
            dur_vals = df_active["DURATION"]

            is_scatter = type_lower.str.contains("scatter", regex=False)
            is_gather = type_lower.str.contains("gather", regex=False)
            is_allred = type_lower.str.contains("all_reduce|allreduce", regex=True)
            is_stall = type_lower.str.contains("stall", regex=False)

            scatter = float(dur_vals[is_scatter].sum())
            gather = float(dur_vals[is_gather].sum())
            all_red = float(dur_vals[is_allred].sum())
            transit = scatter + gather + all_red
            stall = float(dur_vals[is_stall].sum())
            non_comp_mask = is_scatter | is_gather | is_stall | is_allred
            compute = float(dur_vals[~non_comp_mask].sum())

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

    # 3. Métricas de packet_tracking_debug.csv para el ámbito seleccionado (usando caché compacta)
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
            df_p, seg_bounds_csv = load_packet_csv_cached(folder)
            if df_p is not None and not df_p.empty and "Creation_Cycle" in df_p.columns and seg_bounds_csv:
                if target_iter_mode == "all":
                    df_slice = df_p
                else:
                    c_idx = min(target_iter_mode, len(seg_bounds_csv) - 1)
                    s_c, e_c = seg_bounds_csv[c_idx]
                    df_slice = df_p.iloc[s_c:e_c]

                total_packets = len(df_slice)
                if total_packets > 0:
                    if "Num_Flits" in df_slice.columns:
                        total_flits = int(df_slice["Num_Flits"].to_numpy(dtype=np.int64, copy=False).sum())
                    else:
                        total_flits = total_packets * 9

                    cr_arr = df_slice["Creation_Cycle"].to_numpy(dtype=np.float64, copy=False)
                    rx_arr = df_slice["Receive_Cycle"].to_numpy(dtype=np.float64, copy=False)

                    if "Op_Type" in df_slice.columns and "Op_Idx" in df_slice.columns:
                        agg_dict = {
                            "rx_max": ("Receive_Cycle", "max"),
                            "cr_min": ("Creation_Cycle", "min"),
                        }
                        if "Num_Flits" in df_slice.columns:
                            agg_dict["flits"] = ("Num_Flits", "sum")
                        else:
                            agg_dict["pkts"] = ("PID", "count")

                        grp_df = df_slice.groupby(["Op_Type", "Op_Idx"], observed=True, sort=False).agg(**agg_dict)
                        if not grp_df.empty:
                            durs = np.maximum(
                                1.0,
                                grp_df["rx_max"].to_numpy(dtype=np.float64) - grp_df["cr_min"].to_numpy(dtype=np.float64),
                            )
                            f_cnts = (
                                grp_df["flits"].to_numpy(dtype=np.float64)
                                if "flits" in grp_df.columns
                                else grp_df["pkts"].to_numpy(dtype=np.float64) * 9.0
                            )
                            lambda_rate = float(np.mean(f_cnts / (num_gpus * durs)))
                        else:
                            dur_cycles = max(1.0, cluster_wall_clock_ns)
                            lambda_rate = total_flits / (num_gpus * dur_cycles)
                    else:
                        dur = max(1.0, float(rx_arr.max() - cr_arr.min()))
                        lambda_rate = float(total_flits / (num_gpus * dur))

                    if "Total_Latency" in df_slice.columns:
                        avg_pkt_lat = float(np.mean(df_slice["Total_Latency"].to_numpy(dtype=np.float64, copy=False)))
                    else:
                        avg_pkt_lat = float(np.mean(rx_arr - cr_arr))

                    if "Avg_Flit_Latency" in df_slice.columns:
                        avg_flit_lat = float(np.mean(df_slice["Avg_Flit_Latency"].to_numpy(dtype=np.float64, copy=False)))
                    else:
                        avg_flit_lat = avg_pkt_lat

                    if "Queueing_Delay" in df_slice.columns:
                        avg_queue_delay = float(np.mean(df_slice["Queueing_Delay"].to_numpy(dtype=np.float64, copy=False)))
                    elif "Inject_Cycle" in df_slice.columns:
                        inj_arr = df_slice["Inject_Cycle"].to_numpy(dtype=np.float64, copy=False)
                        avg_queue_delay = float(np.mean(inj_arr - cr_arr))
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

    res = {
        "metadata": metadata,
        "kpis": kpis_data,
        **metadata,
        **kpis_data
    }
    if sig is not None:
        with _RESULT_CACHE_LOCK:
            _SUMMARY_CACHE[cache_key] = {"sig": sig, "data": res}
            _SUMMARY_CACHE.move_to_end(cache_key)
            while len(_SUMMARY_CACHE) > _RESULT_CACHE_MAX:
                _SUMMARY_CACHE.popitem(last=False)
    return res


_RE_SHARED_EXP = re.compile(r"shared_expert_ffn_(\d+)")
_RE_EXP_FFN = re.compile(r"expert_ffn_(\d+)")


def _classify_trc_op(raw_type, raw_details):
    """Fast semantic classifier for a single .trc operation row."""
    t = raw_type.lower()
    d = raw_details.lower()
    op = f"{t} {d}"

    if "all_reduce" in op or "allreduce" in op:
        return "all_reduce", "#8e44ad", "AllReduce", "AllReduce", None
    if "scatter" in op:
        return "scatter", "#3498db", "Scatter", "Scatter", None
    if "gather" in op:
        return "gather", "#3498db", "Gather", "Gather", None
    if "stall" in op:
        return "stall", "#e74c3c", "Stall", "Stall", None

    if "shared_expert" in op:
        shared_m = _RE_SHARED_EXP.search(op)
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

    exp_m = _RE_EXP_FFN.search(op)
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
    if "attentiongen" in op or "self_attention" in op:
        return "calc", "#2ecc71", "Attention", "AttnGen", None
    if "attn_o_proj" in op or "attn_o_up_proj" in op:
        return "calc", "#2ecc71", "Attention", "O_Proj", None
    if "input_layer_norm" in op or "post_attn_layer_norm" in op:
        return "calc", "#2ecc71", "Attention", "LN", None
    if "residual_1" in op:
        return "calc", "#2ecc71", "Attention", "Res1", None
    if "gate_fn" in op:
        return "calc", "#2ecc71", "Attention", "Gate", None
    if "residual_2" in op:
        return "calc", "#2ecc71", "Residual", "Res2", None
    if "attn" in op or "attention" in op or "rope" in op or "latent" in op:
        micro = "MLA_Proj"
        if "mla" in op:
            micro = "MLA_Gen"
        elif "rope" in op:
            micro = "RoPE"
        elif "proj" in op:
            micro = "Proj"
        return "calc", "#2ecc71", "Attention", micro, None

    sub = "Linear" if "pop_operation" in op else raw_type[:10]
    return "calc", "#2ecc71", sub, sub, None


def parse_single_trc_segment(df, gpu_id, offset_ns=0.0, iter_num=1):
    """
    Vectorized parser for a single contiguous DataFrame segment (one iteration) of a .trc file.
    Avoids .apply() and .iterrows() while preserving exact sub_ops and mem_bound_pct math.
    Applies offset_ns to all absolute timestamps (start_ns, end_ns, sub_ops).
    """
    if df.empty:
        return []

    dur_mask = (df["DURATION"] > 0).to_numpy()
    if not dur_mask.any():
        return []
    if not dur_mask.all():
        df = df.iloc[dur_mask]

    n_rows = len(df)
    if n_rows == 0:
        return []

    # 1. Extracción vectorizada de capa
    explicit_series = pd.to_numeric(
        df["DETAILS"].str.extract(r"(?:MoE_decoder_|decoder_)(\d+)", expand=False),
        errors="coerce",
    )
    exp_arr = explicit_series.to_numpy(dtype=np.float64, copy=True)
    is_norm = df["TYPE"].str.lower().str.contains("input_layer_norm", regex=False).to_numpy()
    norm_missing_idx = np.flatnonzero(np.isnan(exp_arr) & is_norm)
    for i in norm_missing_idx:
        for j in range(i + 1, min(i + 5, n_rows)):
            if not np.isnan(exp_arr[j]):
                exp_arr[i] = exp_arr[j]
                break
    layers_arr = pd.Series(exp_arr).ffill().bfill().fillna(0).to_numpy(dtype=np.int32)

    # 2. Métricas vectorizadas Comp_ns y Mem_ns
    comp_arr = (
        pd.to_numeric(df["DETAILS"].str.extract(r"Comp_ns:([0-9.]+)", expand=False), errors="coerce")
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
    )
    mem_arr = (
        pd.to_numeric(df["DETAILS"].str.extract(r"Mem_ns:([0-9.]+)", expand=False), errors="coerce")
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
    )

    start_arr = df["START_NS"].to_numpy(dtype=np.float64, copy=False) + offset_ns
    end_arr = df["END_NS"].to_numpy(dtype=np.float64, copy=False) + offset_ns
    dur_arr = df["DURATION"].to_numpy(dtype=np.float64, copy=False)

    # 3. Clasificación semántica rápida sin pandas apply()
    types_list = df["TYPE"].tolist()
    details_list = df["DETAILS"].tolist()
    classified = [_classify_trc_op(t, d) for t, d in zip(types_list, details_list)]

    cats = [c[0] for c in classified]
    colors = [c[1] for c in classified]
    macros = [c[2] for c in classified]
    micros = [c[3] for c in classified]
    exp_ids = [c[4] for c in classified]
    layers_list = layers_arr.tolist()

    # 4. Fronteras contiguas por (LAYER, CATEGORY, MACRO_OP)
    group_starts = [0]
    for i in range(1, n_rows):
        if layers_list[i] != layers_list[i - 1] or cats[i] != cats[i - 1] or macros[i] != macros[i - 1]:
            group_starts.append(i)
    group_starts.append(n_rows)

    start_list = start_arr.tolist()
    end_list = end_arr.tolist()
    dur_list = dur_arr.tolist()
    comp_list = comp_arr.tolist()
    mem_list = mem_arr.tolist()

    blocks = []
    for idx_g in range(len(group_starts) - 1):
        s = group_starts[idx_g]
        e = group_starts[idx_g + 1]

        start_ns = float(start_arr[s:e].min())
        end_ns = float(end_arr[s:e].max())
        dur_ns = end_ns - start_ns
        category = cats[s]
        color = colors[s]
        macro_op = macros[s]
        layer = int(layers_list[s])

        # Fronteras internas y desglose de micro-operaciones (sin .iterrows())
        sub_ops = []
        for st, en, r_dur, mic, c_ns, m_ns in zip(
            start_list[s:e], end_list[s:e], dur_list[s:e], micros[s:e], comp_list[s:e], mem_list[s:e]
        ):
            if r_dur > 0.0:
                denom = c_ns + m_ns
                s_mem = round(min(100.0, max(0.0, (m_ns / denom) * 100.0)), 1) if denom > 0.0 else 0.0
                sub_ops.append({
                    "start_ns": round(st, 1),
                    "duration_ns": round(r_dur, 1),
                    "name": mic,
                    "mem_pct": s_mem,
                })

        micro_slice = micros[s:e]
        if macro_op == "Attention":
            if any("mla" in u.lower() or "rope" in u.lower() for u in micro_slice):
                seq_str = "(LN + MLA_Compress + RoPE + Absorb_Gen + Up_Proj + O_Proj + Res)"
            else:
                seq_str = "(LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)"
        elif macro_op == "DenseFFN":
            seq_str = "(DenseFFN: Gate_Proj + SiLU + Up_Proj + Down_Proj)"
        elif macro_op == "SharedExpert":
            seq_str = "(SharedExp#0: Gate_Proj + SiLU + Up_Proj + Down_Proj)"
        elif macro_op == "ExpertFFN":
            exp_vals = sorted({int(x) for x in exp_ids[s:e] if x is not None})
            if len(exp_vals) == 1:
                seq_str = f"(Exp#{exp_vals[0]}: Gate_Proj + SiLU + Up_Proj + Down_Proj)"
            elif len(exp_vals) > 1:
                if len(exp_vals) <= 3:
                    ids_str = ",".join(str(x) for x in exp_vals)
                    seq_str = f"(Exp#{ids_str}: {len(exp_vals)}x[Gate+SiLU+Up+Down])"
                else:
                    seq_str = f"(Exp#{exp_vals[0]}..#{exp_vals[-1]}: {len(exp_vals)}x[Gate+SiLU+Up+Down])"
            else:
                seq_str = "(ExpertFFN: Gate + SiLU + Up + Down)"
        elif category in ("scatter", "gather", "all_reduce", "stall"):
            seq_str = ""
        else:
            unique_micros = list(dict.fromkeys(micro_slice))
            seq_str = f"({' + '.join(unique_micros)})"

        tot_comp = float(comp_arr[s:e].sum())
        tot_mem = float(mem_arr[s:e].sum())
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
            "local_net": None,
        })

    return blocks


def parse_single_trc(filepath, iteration="last", iteration_offsets=None):
    """
    Parses a single .trc file using cached DataFrame views. Depending on iteration, extracts either
    a single iteration ('last' or '1'..'N') or concatenates all iterations with offsets ('all').
    """
    basename = os.path.basename(filepath)
    try:
        gpu_id = int(basename.split("_")[-1].split(".")[0])
    except Exception:
        gpu_id = 0

    df, seg_bounds = _load_trc_cached(filepath)
    if df.empty or not seg_bounds:
        return []

    num_iters = len(seg_bounds)

    if iteration == "all":
        all_blocks = []
        for k, (s_b, e_b) in enumerate(seg_bounds):
            off = iteration_offsets[k] if (iteration_offsets and k < len(iteration_offsets)) else 0.0
            blocks_k = parse_single_trc_segment(df.iloc[s_b:e_b], gpu_id, offset_ns=off, iter_num=k + 1)
            all_blocks.extend(blocks_k)
        return all_blocks
    elif iteration == "last":
        s_b, e_b = seg_bounds[-1]
        return parse_single_trc_segment(df.iloc[s_b:e_b], gpu_id, offset_ns=0.0, iter_num=num_iters)
    else:
        try:
            val = int(iteration) - 1
            idx = max(0, min(val, num_iters - 1))
        except ValueError:
            idx = num_iters - 1
        s_b, e_b = seg_bounds[idx]
        return parse_single_trc_segment(df.iloc[s_b:e_b], gpu_id, offset_ns=0.0, iter_num=idx + 1)


def _get_folder_sig(folder):
    """Lightweight mtime+size signature for all .trc, metadata, and packet CSV in folder."""
    files = sorted(glob.glob(str(folder / "*device_*.trc")))
    for extra_name in ("packet_tracking_debug.csv", "gui_metadata.json"):
        p = folder / extra_name
        if p.exists():
            files.append(str(p))
    try:
        return tuple((f, os.stat(f).st_mtime_ns, os.stat(f).st_size) for f in files)
    except OSError:
        return None


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

    cache_key = (str(folder), str(iteration))
    sig = _get_folder_sig(folder)
    if sig is not None:
        with _RESULT_CACHE_LOCK:
            cached = _CHRONO_CACHE.get(cache_key)
            if cached is not None and cached["sig"] == sig:
                _CHRONO_CACHE.move_to_end(cache_key)
                return cached["data"]

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

    # Organizar tracks individuales por GPU (sin duplicar all_blocks en 'blocks' para no doblar el payload JSON)
    tracks = [[] for _ in range(num_gpus)]
    for b in all_blocks:
        b["block_type"] = b["category"]
        if b.get("local_net"):
            b["local_packets"] = b["local_net"].get("pkts", 0)
            b["local_flits"] = b["local_net"].get("flits", 0)
            b["avg_lat_cycles"] = b["local_net"].get("avg_lat_cycles", 0.0)
            b["throughput_flits_per_cycle"] = b["local_net"].get("prod_flits_cycle", 0.0)
        tracks[b["gpu_id"]].append(b)

    total_blocks_count = len(all_blocks)
    del all_blocks

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

    res = {
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
        "total_blocks": total_blocks_count,
        "tracks": tracks,
        "blocks": []
    }
    if sig is not None:
        with _RESULT_CACHE_LOCK:
            _CHRONO_CACHE[cache_key] = {"sig": sig, "data": res}
            _CHRONO_CACHE.move_to_end(cache_key)
            while len(_CHRONO_CACHE) > _RESULT_CACHE_MAX:
                _CHRONO_CACHE.popitem(last=False)
    return res


def get_packet_tracking_data(folder_path, offset=0, limit=150, regime="custom", iteration="last"):
    """
    Reads packet_tracking_debug.csv via cache, filters according to iteration without copying
    full DataFrames, and returns a paginated slice supporting regime presets ('free', 'medium', 'critical', 'custom').
    """
    folder = Path(folder_path).resolve()
    df, seg_bounds = load_packet_csv_cached(folder)
    if df is None or df.empty or "Creation_Cycle" not in df.columns or not seg_bounds:
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

    num_iters, _, offsets = get_cluster_iteration_info(folder)
    num_csv_iters = len(seg_bounds)

    if iteration == "all":
        seg_view = df
        if num_csv_iters > 1 and any(o > 0 for o in offsets[:num_csv_iters]):
            op_offsets = np.zeros(len(df), dtype=np.float64)
            for k, (s_b, e_b) in enumerate(seg_bounds):
                if k < len(offsets) and offsets[k] > 0:
                    op_offsets[s_b:e_b] = offsets[k]
        else:
            op_offsets = None
    elif iteration == "last":
        s_b, e_b = seg_bounds[-1]
        seg_view = df.iloc[s_b:e_b]
        op_offsets = None
    else:
        try:
            val = int(iteration) - 1
            idx = max(0, min(val, num_csv_iters - 1))
        except ValueError:
            idx = num_csv_iters - 1
        s_b, e_b = seg_bounds[idx]
        seg_view = df.iloc[s_b:e_b]
        op_offsets = None

    total_pkts = len(seg_view)
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

    with (_HEAVY_DF_OP_LOCK if total_pkts > 1_000_000 else nullcontext()):
        pid_arr = seg_view["PID"].to_numpy(copy=False)
        order = np.argsort(pid_arr, kind="mergesort")

        # Selección de régimen sin ordenar/copiar el DataFrame entero
        regime = str(regime).lower().strip()
        limit = max(10, min(int(limit), 500))
        if regime == "free":
            effective_offset = 0
        elif regime in ("medium", "critical"):
            if "Total_Latency" in seg_view.columns:
                tot_lat_all = seg_view["Total_Latency"].to_numpy(copy=False)
            else:
                tot_lat_all = (
                    seg_view["Receive_Cycle"].to_numpy(copy=False)
                    - seg_view["Creation_Cycle"].to_numpy(copy=False)
                )
            tot_lat_ordered = tot_lat_all[order]
            if regime == "medium":
                med_val = float(np.median(tot_lat_ordered))
                med_pos = int(np.abs(tot_lat_ordered - med_val).argmin())
                effective_offset = max(0, med_pos - limit // 2)
            else:
                max_pos = int(tot_lat_ordered.argmax())
                effective_offset = max(0, max_pos - limit // 2)
            del tot_lat_ordered
        else:
            effective_offset = max(0, min(int(offset), total_pkts - 1))

        sel_idx = order[effective_offset : effective_offset + limit]
        del order
        df_slice = seg_view.iloc[sel_idx].copy()
    if op_offsets is not None and "Op_Start_NS" in df_slice.columns:
        df_slice["Op_Start_NS"] = df_slice["Op_Start_NS"].to_numpy(dtype=np.float64) + op_offsets[sel_idx]

    # Normalización para trazas legacy con Creation_Cycle absoluto (> 1e7)
    is_legacy = not seg_view.empty and float(seg_view["Creation_Cycle"].min()) > 1e7
    if is_legacy and "Op_Type" in df_slice.columns and "Op_Idx" in df_slice.columns:
        base_map = (
            seg_view.groupby(["Op_Type", "Op_Idx"], observed=True)["Creation_Cycle"]
            .min()
            .to_dict()
        )
        base_cycles = np.array(
            [base_map.get((ot, oi), 0.0) for ot, oi in zip(df_slice["Op_Type"], df_slice["Op_Idx"])],
            dtype=np.float64,
        )
    else:
        base_cycles = np.zeros(len(df_slice), dtype=np.float64)

    cr_arr = df_slice["Creation_Cycle"].to_numpy(dtype=np.float64) - base_cycles
    inj_arr = (
        df_slice["Inject_Cycle"].to_numpy(dtype=np.float64) - base_cycles
        if "Inject_Cycle" in df_slice.columns
        else cr_arr
    )
    rx_arr = df_slice["Receive_Cycle"].to_numpy(dtype=np.float64) - base_cycles

    q_arr = (
        df_slice["Queueing_Delay"].to_numpy(dtype=np.float64)
        if "Queueing_Delay" in df_slice.columns
        else np.maximum(0.0, inj_arr - cr_arr)
    )
    net_arr = (
        df_slice["Network_Latency"].to_numpy(dtype=np.float64)
        if "Network_Latency" in df_slice.columns
        else np.maximum(0.0, rx_arr - inj_arr)
    )
    tot_arr = (
        df_slice["Total_Latency"].to_numpy(dtype=np.float64)
        if "Total_Latency" in df_slice.columns
        else (q_arr + net_arr)
    )
    flits_arr = (
        df_slice["Num_Flits"].to_numpy(dtype=np.int64)
        if "Num_Flits" in df_slice.columns
        else np.full(len(df_slice), 9, dtype=np.int64)
    )
    size_arr = (
        df_slice["Size_Bytes"].to_numpy(dtype=np.int64)
        if "Size_Bytes" in df_slice.columns
        else flits_arr * 32
    )
    avg_flit_arr = (
        df_slice["Avg_Flit_Latency"].to_numpy(dtype=np.float64)
        if "Avg_Flit_Latency" in df_slice.columns
        else tot_arr
    )
    prod_arr = (
        df_slice["Throughput"].to_numpy(dtype=np.float64)
        if "Throughput" in df_slice.columns
        else np.zeros(len(df_slice), dtype=np.float64)
    )

    min_cycle = float(cr_arr.min()) if len(cr_arr) > 0 else 0.0
    max_cycle = float(rx_arr.max()) if len(rx_arr) > 0 else 1.0
    op_start_arr = (
        df_slice["Op_Start_NS"].to_numpy(dtype=np.float64)
        if "Op_Start_NS" in df_slice.columns
        else np.zeros(len(df_slice), dtype=np.float64)
    )
    op_end_arr = (
        df_slice["Op_End_NS"].to_numpy(dtype=np.float64)
        if "Op_End_NS" in df_slice.columns
        else (op_start_arr + tot_arr)
    )

    pid_slice = df_slice["PID"].to_numpy(dtype=np.int64).tolist()
    src_slice = df_slice["Source"].to_numpy(dtype=np.int64).tolist()
    dst_slice = df_slice["Dest"].to_numpy(dtype=np.int64).tolist()
    op_t_slice = [str(x) for x in df_slice["Op_Type"].tolist()] if "Op_Type" in df_slice.columns else ["Scatter"] * len(df_slice)
    op_i_slice = [int(x) if pd.notna(x) else 1 for x in df_slice["Op_Idx"].tolist()] if "Op_Idx" in df_slice.columns else [1] * len(df_slice)

    packets = []
    for (pid, src, dst, op_t, op_i, flits, size_b, c_cyc, inj_cyc, rx_cyc,
         q_del, net_l, tot_l, avg_f, prod, p_op_s, p_op_e) in zip(
        pid_slice, src_slice, dst_slice, op_t_slice, op_i_slice,
        flits_arr.tolist(), size_arr.tolist(),
        cr_arr.tolist(), inj_arr.tolist(), rx_arr.tolist(),
        q_arr.tolist(), net_arr.tolist(), tot_arr.tolist(),
        avg_flit_arr.tolist(), prod_arr.tolist(),
        op_start_arr.tolist(), op_end_arr.tolist()
    ):
        packets.append({
            "pid": pid,
            "src": src,
            "dst": dst,
            "op_type": op_t,
            "op_idx": op_i,
            "flits": flits,
            "num_flits": flits,
            "size_bytes": size_b,
            "creation_cycle": c_cyc,
            "inject_cycle": inj_cyc,
            "receive_cycle": rx_cyc,
            "queueing_delay": q_del,
            "queue_delay_cycles": q_del,
            "network_latency": net_l,
            "flight_cycles": net_l,
            "total_latency": tot_l,
            "total_latency_cycles": tot_l,
            "avg_flit_latency": round(avg_f, 2),
            "throughput": round(prod, 2),
            "op_start_ns": p_op_s,
            "op_end_ns": p_op_e,
            "global_create_ns": p_op_s + c_cyc,
            "global_inject_ns": p_op_s + inj_cyc,
            "global_receive_ns": p_op_s + rx_cyc,
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


def get_packets_in_time_window(folder_path, start_ns, end_ns, iteration="last", max_packets=SAFE_MAX_PACKETS):
    """
    Returns in-flight packets whose lifecycle [pkt_start_ns, pkt_end_ns]
    overlaps with the visible time window [start_ns, end_ns] in global nanoseconds.
    Uses thread-safe cached CSV + minimal-footprint NumPy window filtering.
    Enforces adaptive safe cap (SAFE_MAX_PACKETS=2500): returns 100% exact when <=2500,
    or deterministic uniform stratified sampling of 2500 packets when >2500.
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
        df, seg_bounds = load_packet_csv_cached(folder)
        if df is None or df.empty or "Creation_Cycle" not in df.columns or not seg_bounds:
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

        num_iters, _, offsets = get_cluster_iteration_info(folder)

        if iteration == "all":
            slices_to_process = [
                (k, seg_bounds[k], offsets[k] if k < len(offsets) else 0.0)
                for k in range(len(seg_bounds))
            ]
        elif iteration == "last":
            slices_to_process = [(len(seg_bounds) - 1, seg_bounds[-1], 0.0)]
        else:
            try:
                val = int(iteration) - 1
                idx = max(0, min(val, len(seg_bounds) - 1))
            except ValueError:
                idx = len(seg_bounds) - 1
            slices_to_process = [(idx, seg_bounds[idx], 0.0)]

        # Enforce safe adaptive cap (default/0 -> SAFE_MAX_PACKETS=2500, upper bounded by 2500)
        if max_packets is None or int(max_packets) <= 0:
            effective_cap = SAFE_MAX_PACKETS
        else:
            effective_cap = max(10, min(int(max_packets), SAFE_MAX_PACKETS))

        with (_HEAVY_DF_OP_LOCK if len(df) > 1_000_000 else nullcontext()):
            matched_global_idx = []
            matched_start_ns = []
            slice_off_meta = []  # (len_hits, off_ns, is_legacy, base_arr_or_None)

            for _, (s_b, e_b), off_ns in slices_to_process:
                if e_b <= s_b:
                    continue
                seg = df.iloc[s_b:e_b]
                cr_arr = seg["Creation_Cycle"].to_numpy(copy=False)
                rx_arr = seg["Receive_Cycle"].to_numpy(copy=False)
                op_start_arr = seg["Op_Start_NS"].to_numpy(copy=False)

                is_legacy = cr_arr.min() > 1e7 and "Op_Type" in seg.columns and "Op_Idx" in seg.columns
                if is_legacy:
                    base_cycles = seg.groupby(["Op_Type", "Op_Idx"], observed=True)["Creation_Cycle"].transform("min").to_numpy(dtype=np.float64)
                    pkt_start = (op_start_arr + off_ns) + (cr_arr - base_cycles)
                    mask_s = pkt_start <= end_ns
                    cand_rel = np.flatnonzero(mask_s)
                    del mask_s
                    if len(cand_rel) > 0:
                        pkt_end_cand = (op_start_arr[cand_rel] + off_ns) + (rx_arr[cand_rel] - base_cycles[cand_rel])
                        rel_hits = cand_rel[pkt_end_cand >= start_ns]
                        del pkt_end_cand
                    else:
                        rel_hits = cand_rel
                    del cand_rel
                else:
                    base_cycles = None
                    pkt_start = op_start_arr + cr_arr
                    if off_ns != 0.0:
                        pkt_start += off_ns
                    mask_s = pkt_start <= end_ns
                    cand_rel = np.flatnonzero(mask_s)
                    del mask_s
                    if len(cand_rel) > 0:
                        pkt_end_cand = op_start_arr[cand_rel] + rx_arr[cand_rel]
                        if off_ns != 0.0:
                            pkt_end_cand += off_ns
                        rel_hits = cand_rel[pkt_end_cand >= start_ns]
                        del pkt_end_cand
                    else:
                        rel_hits = cand_rel
                    del cand_rel

                if len(rel_hits) > 0:
                    matched_global_idx.append((rel_hits + s_b).astype(np.int32))
                    matched_start_ns.append(pkt_start[rel_hits])
                    slice_off_meta.append((len(rel_hits), off_ns, base_cycles[rel_hits] if base_cycles is not None else None))

                del pkt_start, base_cycles

            if not matched_global_idx:
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

            g_idx = matched_global_idx[0] if len(matched_global_idx) == 1 else np.concatenate(matched_global_idx)
            m_start = matched_start_ns[0] if len(matched_start_ns) == 1 else np.concatenate(matched_start_ns)
            del matched_global_idx, matched_start_ns

            total_in_window = len(g_idx)

            if total_in_window > effective_cap:
                time_order = np.argsort(m_start, kind="mergesort")
                sample_pos = np.linspace(0, total_in_window - 1, effective_cap, dtype=int)
                chosen_rel = time_order[sample_pos]
                del time_order
                truncated = True
            else:
                pid_m = df["PID"].to_numpy(copy=False)[g_idx]
                chosen_rel = np.lexsort((pid_m, m_start))
                truncated = False

            sel_g = g_idx[chosen_rel]
            sel_start = m_start[chosen_rel]
            del g_idx, m_start

            if truncated:
                pid_sel = df["PID"].to_numpy(copy=False)[sel_g]
                re_ord = np.lexsort((pid_sel, sel_start))
                sel_g = sel_g[re_ord]
                sel_start = sel_start[re_ord]
                chosen_rel = chosen_rel[re_ord]

            # Resolve per-selected-row offsets and legacy base cycles (only <=2500 elements!)
            has_nonzero_off = any(m[1] != 0.0 for m in slice_off_meta)
            has_legacy_base = any(m[2] is not None for m in slice_off_meta)
            if has_nonzero_off or has_legacy_base:
                sel_off = np.zeros(len(chosen_rel), dtype=np.float64)
                sel_base = np.zeros(len(chosen_rel), dtype=np.float64)
                cum_ends = np.cumsum([m[0] for m in slice_off_meta])
                cum_starts = np.concatenate(([0], cum_ends[:-1]))
                for out_i, r_pos in enumerate(chosen_rel):
                    for seg_k, (cs, ce) in enumerate(zip(cum_starts, cum_ends)):
                        if cs <= r_pos < ce:
                            sel_off[out_i] = slice_off_meta[seg_k][1]
                            if slice_off_meta[seg_k][2] is not None:
                                sel_base[out_i] = slice_off_meta[seg_k][2][r_pos - cs]
                            break
            else:
                sel_off = 0.0
                sel_base = 0.0

            del chosen_rel, slice_off_meta

            sub = df.iloc[sel_g]
            sel_op_start = sub["Op_Start_NS"].to_numpy(dtype=np.float64) + sel_off
            sel_cr = sub["Creation_Cycle"].to_numpy(dtype=np.float64) - sel_base
            sel_inj = (sub["Inject_Cycle"].to_numpy(dtype=np.float64) - sel_base) if "Inject_Cycle" in sub.columns else sel_cr
            sel_rx = sub["Receive_Cycle"].to_numpy(dtype=np.float64) - sel_base

        sel_inject = sel_op_start + sel_inj
        sel_end = sel_op_start + sel_rx

        pids = sub["PID"].to_numpy(dtype=np.int64).tolist()
        srcs = sub["Source"].to_numpy(dtype=np.int64).tolist()
        dsts = sub["Dest"].to_numpy(dtype=np.int64).tolist()
        op_types = [str(x) for x in sub["Op_Type"].tolist()] if "Op_Type" in sub.columns else ["Scatter"] * len(sub)
        op_idxs = [int(x) if pd.notna(x) else 1 for x in sub["Op_Idx"].tolist()] if "Op_Idx" in sub.columns else [1] * len(sub)
        flits_l = sub["Num_Flits"].to_numpy(dtype=np.int64).tolist() if "Num_Flits" in sub.columns else [9] * len(sub)

        if "Queueing_Delay" in sub.columns:
            q_delays = sub["Queueing_Delay"].to_numpy(dtype=np.float64).tolist()
        else:
            q_delays = np.maximum(0.0, sel_inject - sel_start).tolist()

        if "Network_Latency" in sub.columns:
            net_lats = sub["Network_Latency"].to_numpy(dtype=np.float64).tolist()
        else:
            net_lats = np.maximum(0.0, sel_end - sel_inject).tolist()

        if "Total_Latency" in sub.columns:
            tot_lats = sub["Total_Latency"].to_numpy(dtype=np.float64).tolist()
        else:
            tot_lats = (sel_end - sel_start).tolist()

        packets = []
        for pid, src, dst, op_t, op_i, flits, q_d, net_l, tot_l, p_s, p_i, p_e in zip(
            pids, srcs, dsts, op_types, op_idxs, flits_l, q_delays, net_lats, tot_lats,
            sel_start.tolist(), sel_inject.tolist(), sel_end.tolist()
        ):
            packets.append({
                "pid": pid,
                "src": src,
                "dst": dst,
                "op_type": op_t,
                "op_idx": op_i,
                "flits": flits,
                "queue_delay_cycles": round(q_d, 1),
                "flight_cycles": round(net_l, 1),
                "total_latency_cycles": round(tot_l, 1),
                "pkt_start_ns": round(p_s, 1),
                "pkt_inject_ns": round(p_i, 1),
                "pkt_end_ns": round(p_e, 1),
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
            df_t, segs_b = _load_trc_cached(tf)
            if df_t.empty or not segs_b:
                continue

            if target_iter_mode == "all":
                df_act = df_t
            else:
                s_idx = min(target_iter_mode, len(segs_b) - 1)
                s_b, e_b = segs_b[s_idx]
                df_act = df_t.iloc[s_b:e_b]

            type_lower = df_act["TYPE"].str.lower()
            dur_vals = df_act["DURATION"]
            is_scatter = type_lower.str.contains("scatter", regex=False)
            is_gather = type_lower.str.contains("gather", regex=False)
            is_allred = type_lower.str.contains("all_reduce|allreduce", regex=True)
            is_stall = type_lower.str.contains("stall", regex=False)

            scat = float(dur_vals[is_scatter].sum())
            gath = float(dur_vals[is_gather].sum())
            ar = float(dur_vals[is_allred].sum())
            trans = scat + gath + ar
            stl = float(dur_vals[is_stall].sum())
            non_comp = is_scatter | is_gather | is_stall | is_allred
            comp = float(dur_vals[~non_comp].sum())

            gpu_times[d_id] = {
                "compute_us": round(comp / 1000.0, 2),
                "transit_us": round(trans / 1000.0, 2),
                "stall_us": round(stl / 1000.0, 2)
            }
        except Exception:
            pass

    # 4. Datos de paquetes NoC desde packet_tracking_debug.csv (usando caché compartida)
    csv_path = folder / "packet_tracking_debug.csv"
    has_packet_data = csv_path.exists()
    flows = []
    total_slice_packets = 0
    total_slice_flits = 0

    tx_stats = {d: {"pkts": 0, "flits": 0, "q_avg": 0.0} for d in range(num_gpus)}
    rx_stats = {d: {"pkts": 0, "flits": 0, "lat_avg": 0.0} for d in range(num_gpus)}

    if has_packet_data:
        try:
            df_p, segs_csv = load_packet_csv_cached(folder)
            if df_p is not None and not df_p.empty and "Source" in df_p.columns and "Dest" in df_p.columns and segs_csv:
                if target_iter_mode == "all":
                    df_slice = df_p
                else:
                    c_idx = min(target_iter_mode, len(segs_csv) - 1)
                    s_c, e_c = segs_csv[c_idx]
                    df_slice = df_p.iloc[s_c:e_c]

                # Filtro por fase de operación colectiva
                f_op = op_filter.lower().strip()
                if "Op_Type" in df_slice.columns:
                    op_str = df_slice["Op_Type"].astype(str).str.lower()
                    if f_op in ["scatter", "moe scatter"]:
                        df_filtered = df_slice[op_str.str.contains("scatter", regex=False, na=False)]
                    elif f_op in ["gather", "moe gather"]:
                        df_filtered = df_slice[op_str.str.contains("gather", regex=False, na=False)]
                    elif f_op in ["allreduce", "ring-allreduce", "all_reduce"]:
                        df_filtered = df_slice[op_str.str.contains("all_reduce|allreduce", regex=True, na=False)]
                    else:
                        df_filtered = df_slice
                else:
                    df_filtered = df_slice

                total_slice_packets = len(df_filtered)
                has_flits = "Num_Flits" in df_filtered.columns
                total_slice_flits = int(df_filtered["Num_Flits"].to_numpy(dtype=np.int64, copy=False).sum()) if (total_slice_packets > 0 and has_flits) else total_slice_packets * 9

                # Agregación vectorizada ultra-rápida por nodo
                if total_slice_packets > 0:
                    has_cycles = all(c in df_filtered.columns for c in ("Creation_Cycle", "Inject_Cycle", "Receive_Cycle"))

                    tx_agg_spec = {"pkts": ("Source", "count")}
                    rx_agg_spec = {"pkts": ("Dest", "count")}
                    if has_flits:
                        tx_agg_spec["flits"] = ("Num_Flits", "sum")
                        rx_agg_spec["flits"] = ("Num_Flits", "sum")
                    if "Queueing_Delay" in df_filtered.columns:
                        tx_agg_spec["q_avg"] = ("Queueing_Delay", "mean")
                    elif has_cycles:
                        tx_agg_spec["sum_inj"] = ("Inject_Cycle", "sum")
                        tx_agg_spec["sum_cr"] = ("Creation_Cycle", "sum")

                    if "Total_Latency" in df_filtered.columns:
                        rx_agg_spec["lat_avg"] = ("Total_Latency", "mean")
                    elif has_cycles:
                        rx_agg_spec["sum_rx"] = ("Receive_Cycle", "sum")
                        rx_agg_spec["sum_cr"] = ("Creation_Cycle", "sum")

                    tx_df_g = df_filtered.groupby("Source", observed=True).agg(**tx_agg_spec)
                    rx_df_g = df_filtered.groupby("Dest", observed=True).agg(**rx_agg_spec)

                    for d in range(num_gpus):
                        if d in tx_df_g.index:
                            r_tx = tx_df_g.loc[d]
                            p_tx = int(r_tx["pkts"])
                            f_tx = int(r_tx["flits"]) if "flits" in r_tx else p_tx * 9
                            if "q_avg" in r_tx:
                                q_tx = float(r_tx["q_avg"])
                            elif "sum_inj" in r_tx and p_tx > 0:
                                q_tx = float(r_tx["sum_inj"] - r_tx["sum_cr"]) / p_tx
                            else:
                                q_tx = 0.0
                        else:
                            p_tx, f_tx, q_tx = 0, 0, 0.0

                        if d in rx_df_g.index:
                            r_rx = rx_df_g.loc[d]
                            p_rx = int(r_rx["pkts"])
                            f_rx = int(r_rx["flits"]) if "flits" in r_rx else p_rx * 9
                            if "lat_avg" in r_rx:
                                l_rx = float(r_rx["lat_avg"])
                            elif "sum_rx" in r_rx and p_rx > 0:
                                l_rx = float(r_rx["sum_rx"] - r_rx["sum_cr"]) / p_rx
                            else:
                                l_rx = 0.0
                        else:
                            p_rx, f_rx, l_rx = 0, 0, 0.0

                        tx_stats[d] = {"pkts": p_tx, "flits": f_tx, "q_avg": round(q_tx, 1)}
                        rx_stats[d] = {"pkts": p_rx, "flits": f_rx, "lat_avg": round(l_rx, 1)}

                    # Agregación vectorizada de flujos (Source -> Dest con s != d)
                    flow_mask = df_filtered["Source"].to_numpy() != df_filtered["Dest"].to_numpy()
                    flow_df = df_filtered.iloc[flow_mask] if not flow_mask.all() else df_filtered
                    if not flow_df.empty:
                        if "Total_Latency" in flow_df.columns and "Queueing_Delay" in flow_df.columns and "Network_Latency" in flow_df.columns:
                            flow_tmp = flow_df
                        else:
                            # Construir dataframe ligero solo con las columnas de flujo necesarias
                            cr_f = flow_df["Creation_Cycle"].to_numpy(dtype=np.int32, copy=False)
                            inj_f = flow_df["Inject_Cycle"].to_numpy(dtype=np.int32, copy=False) if "Inject_Cycle" in flow_df.columns else cr_f
                            rx_f = flow_df["Receive_Cycle"].to_numpy(dtype=np.int32, copy=False)
                            flow_tmp = pd.DataFrame({
                                "Source": flow_df["Source"].to_numpy(copy=False),
                                "Dest": flow_df["Dest"].to_numpy(copy=False),
                                "Num_Flits": flow_df["Num_Flits"].to_numpy(copy=False) if has_flits else np.full(len(flow_df), 9, dtype=np.int16),
                                "Total_Latency": flow_df["Total_Latency"].to_numpy(copy=False) if "Total_Latency" in flow_df.columns else (rx_f - cr_f),
                                "Queueing_Delay": flow_df["Queueing_Delay"].to_numpy(copy=False) if "Queueing_Delay" in flow_df.columns else np.maximum(0, inj_f - cr_f),
                                "Network_Latency": flow_df["Network_Latency"].to_numpy(copy=False) if "Network_Latency" in flow_df.columns else np.maximum(0, rx_f - inj_f),
                            })

                        flow_grp = flow_tmp.groupby(["Source", "Dest"], observed=True).agg(
                            packets=("Num_Flits", "count"),
                            flits=("Num_Flits", "sum"),
                            avg_latency=("Total_Latency", "mean"),
                            avg_queue=("Queueing_Delay", "mean"),
                            max_queue=("Queueing_Delay", "max"),
                            avg_net_lat=("Network_Latency", "mean"),
                        ).reset_index()

                        for s, d, cnt, f_sum, lat_m, q_m, q_max, net_m in zip(
                            flow_grp["Source"].tolist(),
                            flow_grp["Dest"].tolist(),
                            flow_grp["packets"].tolist(),
                            flow_grp["flits"].tolist(),
                            flow_grp["avg_latency"].tolist(),
                            flow_grp["avg_queue"].tolist(),
                            flow_grp["max_queue"].tolist(),
                            flow_grp["avg_net_lat"].tolist(),
                        ):
                            s, d, cnt, f_sum = int(s), int(d), int(cnt), int(f_sum)
                            lat_m = float(lat_m) if pd.notna(lat_m) else 0.0
                            q_m = float(q_m) if pd.notna(q_m) else 0.0
                            q_max = float(q_max) if pd.notna(q_max) else 0.0
                            net_m = float(net_m) if pd.notna(net_m) else max(0.0, lat_m - q_m)
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
