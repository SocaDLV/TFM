# LLM-NoC Co-Simulation Framework

![C++](https://img.shields.io/badge/C++-17-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8+-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

A cycle-accurate, scientifically rigorous co-simulation environment designed to evaluate physical interconnection network bottlenecks in Large Language Models (LLMs), with a dedicated focus on **Mixture of Experts (MoE)** architectures like Mixtral.

This project couples the compute- and memory-graph fidelity of **LLMSimulator** with the flit-level network contention modeling of **BookSim2**, orchestrated by an automated Python CLI workflow for reproducible scientific evaluation.

---

## 📖 Abstract & Motivation

While analytical LLM simulators accurately model silicon compute time (via Roofline models) and static network latencies ($Time = Data / Bandwidth$), they fundamentally fail to capture the dynamic, asymmetrical network contention induced by MoE routing. When tokens are dynamically routed to specialized experts distributed across GPUs (Expert Parallelism), all-to-all traffic bursts rapidly saturate physical interconnects, generating severe queueing delays and long tail latencies.

This framework addresses this limitation by introducing an **"Oracle" co-simulation architecture**:
Rather than relying on static analytical formulas, the compute simulator delegates all collective communication primitives (`AllReduce`, `AllToAll`, `moe_scatter`, and `moe_gather`) directly to an integrated **BookSim2** network backend.

BookSim2 models:
- Physical topology constraints (Torus, Mesh, Ring) and routing algorithms (`dim_order`, `min_adapt`).
- Virtual Channel (VC) allocation, buffer management, and flow-control credits.
- Flit-level collisions, head-of-line blocking, and queueing delays.
- Exact nanosecond completion latencies, feeding back into the compute simulator to induce causal `NETWORK_STALL` synchronization barriers across all GPUs.

---

## 🏗️ Architecture & Core Contributions

* **Compute Engine (LLMSimulator):** Accurately models modern transformer building blocks, Grouped Query Attention (GQA), SwiGLU activations, and MoE routing on state-of-the-art accelerators (e.g., Nvidia B100).
* **Network Engine (BookSim2):** Simulates flit-level packet traversal through routers, crossbars, and physical links.
* **Cycle-Accurate Tensor Parallelism (AllReduce) in BookSim2 (Vía 2):**
  * Models Ring-AllReduce collective communication at flit-level granularity when `tensor_degree > 1` (`none_expert_tensor_degree`).
  * Decomposes input activation tensors ($S_{\text{chunk}} = \lceil \text{size} / P \rceil$) across $P$ GPUs, transferring $2(P-1)S_{\text{chunk}}$ bytes per device through $P-1$ Reduce-Scatter and $P-1$ All-Gather logical ring hops.
  * Governed by asynchronous quadruple causality ($\Delta t$, RX arrival, TX injection, TX retirement) and sub-group isolated latency caching without artificial pre-network clock flattening (`equalize_time = false`).
* **Flit-Level Packet Lifecycle & Network Throughput Tracking (Default Enabled):**
  * High-precision temporal tracking of every retired packet (active by default, bypass with `--no_debug_pids`):
    * **`Creation_Cycle` ($ctime$):** Cycle at which the MoE communication layer generates the packet burst.
    * **`Inject_Cycle` ($itime$):** Cycle at which the head flit leaves the network interface controller (NIC) queue and enters the first router.
    * **`Receive_Cycle` ($atime$):** Cycle at which the tail flit is retired at the destination GPU.
  * Rigorous decomposition of total packet latency into **NIC Queueing Delay** ($itime - ctime$) and **NoC Flight Time** ($atime - itime$).
  * **Flit-Level Network Productivity & Latency Metrics (Cumulative at $atime$):**
    * **Cumulative Operation Average Flit Latency (`Avg_Flit_Latency`):** Exact accumulated mean cycle latency of *all* flits received across the entire collective network operation up to cycle $t_{\text{retire}}$:
      $$\text{Avg\_Flit\_Latency} = \frac{\sum_{\text{all flits in op up to } \_time} (t_{\text{retire}} - ctime)}{\text{Total Flits Received in Op up to } \_time} \quad [\text{cycles}]$$
    * **Cumulative Network Throughput (`Throughput`):** Total flits received in the operation divided by elapsed network cycles:
      $$\text{Throughput} = \frac{\text{Total Flits Received in Op up to } \_time}{\max(1, \_time - t_{\text{start\_op}})} \quad [\text{flits/cycle}]$$
  * **LLM Network Operation Context & Temporal Boundaries:**
    * Automatic attribution of each packet to its LLM collective operation: `Op_Type` (`Scatter` or `Gather`), `Op_Idx` (correlative counter per iteration, reset upon clock drop), and absolute GPU chronogram window `Op_Start_NS` and `Op_End_NS`.
  * Comprehensive logging of Packet ID (`PID`), routing tuple (`Source`, `Dest`), flit count (`Num_Flits`), and physical wire footprint (`Size_Bytes`).
* **Micro-Architectural Hierarchical Tracing:**
  * Propagation of the full C++ module namespace (`module_map_name`) into `.trc` event logs. This disambiguates generic compute entries (`Calc`) into specific operations: **ExpertFFN** (`gate_proj`, `up_proj`, `down_proj`, activations), **Attention** (QKV projections, self-attention, `o_proj`), **Linear**, **LayerNorm**, **Residual**, etc.
* **Rigorous Packetization Modeling:**
  * Precise segmentation into Maximum Transmission Units ($\text{MTU} = 256\text{ B}$), headers ($\text{Header} = 24\text{ B}$), and flits ($\text{Flit Size} = 32\text{ B}$).
  * Exact physical wire modeling: activation vectors of $4096\text{ B}$ (Mixtral) partition into exactly 16 packets with $256\text{ B}$ payload $+ 24\text{ B}$ header $= 280\text{ B}$, requiring $\lceil 280 / 32 \rceil = 9\text{ flits}$ ($288\text{ B}$ physically transferred over the wire).
* **Physical Causality & Asynchronous Interconnect Fidelity (Bloque C):**
  * **Individualized Network Latency per Destination GPU (`latency_per_dst`):** Rather than assigning a uniform scalar duration based on the slowest tail flit of the entire cluster, BookSim2 records the exact arrival cycle `atime` of the last packet destined to each specific GPU $dst$. Each GPU advances its local clock strictly by its own network latency $\text{network\_latency\_ns}[dst] = (t_{\min} + \text{max\_relative\_atime}[dst]) - t_{\text{src}}[dst]$.
  * **Immediate Local Compute Unblocking in MoEScatter:** Scoped synchronization in `sync_for_moe_scatter` allows GPUs receiving fewer tokens to immediately enter `ExpertFFN` local execution without waiting for slower GPUs to finish receiving remote tokens.
  * **Causal Staggered Packet Injection ($\Delta t_{src}$):** When GPUs reach communication phases (`MoEGather`, or unsynchronized `MoEScatter`) at varying timestamps $t_{\text{src}}$, the Oracle computes relative injection delays $\Delta t_{\text{src}} = \text{round}(t_{\text{src}} - t_{\min})$ and dynamically injects packets into BookSim2 exactly when `cycles == delta_t[src]`. Fast GPUs inject and traverse the NoC earlier, realistically modeling dynamic contention.
  * **Emergent Collective Synchronization Stalls (`NETWORK_STALL`):** At the subsequent collective barrier (`sync_for_moe_gather`), faster GPUs wait for straggler GPUs, realistically capturing synchronization bubbles (`NETWORK_STALL`) in trace logs and cycle-to-cycle cronograms.
* **Architectural Corrections & Simulator Stability:**
  * **Clean Trace Initialization (Elimination of 128 Ghost Lines):** Silenced static graph construction executions in `LayerNorm`, `Residual`, `RoPE`, and `Communication` before `Cluster::run()` via explicit `perform_execution` checking, truncating `.trc` files to guarantee execution traces start cleanly at $0.0000\text{ ns}$.
  * Clean Oracle state resets and queue flushing between layers and decoding iterations.
  * Strict synchronization barriers in MoE and SwiGLU dependency chains.
  * Elimination of unconditional timeboard clock overwrites to preserve true asynchronous causality.

---

## ⚙️ Prerequisites & Installation

### Dependencies
* **C++ Compiler:** GCC 9.0+ or Clang with C++17 support.
* **Build System:** CMake 3.15+
* **Python:** 3.8+ with `pandas`, `matplotlib`, and `pyyaml`.

### Build Instructions

```bash
# 1. Clone the repository
git clone <repository-url>
cd TFM

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Compile the Co-Simulator (C++ core + BookSim2)
cd LLMSimulator
mkdir -p build && cd build
cmake ..
make -j$(nproc)
cd ..
```

---

## 🚀 Usage: Automated CLI Workflow (`run_sim.py`)

All simulations and post-processing tools are launched from within the `LLMSimulator/` directory:

```bash
cd LLMSimulator

# Example 1: 1D Torus Topology (8 GPUs) with Batch Size 32 (Packet Tracking automatically generated)
python3 run_sim.py --model mixtral --net_dims 8 --topology torus --vcs 4 --batch_size 32

# Example 2: 2D Mesh Topology (4x4 = 16 GPUs)
python3 run_sim.py --model mixtral --net_dims 4 4 --topology mesh --vcs 4

# Example 3: Fast execution without packet tracing I/O overhead
python3 run_sim.py --model mixtral --net_dims 8 --topology torus --vcs 2 --batch_size 32 --no_debug_pids
```

### Simulation CLI Parameters (`run_sim.py`)

#### Interconnection Network Options (BookSim2)
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--topology` | `str` | `torus` | Physical network topology (`torus`, `mesh`, `ring`). |
| `--net_dims` | `int(s)` | `8` | Symmetrical grid dimensions (e.g., `8` for 1D, `4 4` for 2D). Total GPU count is inferred automatically. |
| `--routing` | `str` | `dim_order` | Routing algorithm (`dim_order`, `min_adapt`). |
| `--vcs` | `int` | `4` | Number of Virtual Channels (VCs). *Note: Torus topologies require $\ge 2$ VCs to prevent routing deadlocks.* |

#### Workload & Model Options (LLMSimulator)
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model` | `str` | `mixtral` | Target LLM architecture (`mixtral`, `llama`). |
| `--batch_size` | `int` | `32` | Maximum concurrent batch size for continuous batching. |
| `--skewness` / `--skew` | `float` | `0.0` | MoE token routing distribution factor (Zipfian exponent $s$). $0.0$ generates uniform routing; $> 0$ concentrates tokens on low-indexed experts, inducing severe network in-cast congestion and barrier stragglers. |
| `--tensor_degree` / `--tp` | `int` | `1` | Tensor Parallelism degree for non-expert layers (Attention/linear projections). When $> 1$, Ring-AllReduce is simulated cycle-accurately in BookSim2. |
| `--input_len` | `int` | `1024` | Prompt length (prefill tokens). |
| `--output_len` | `int` | `10` | Tokens to generate per iteration (drives sustained MoE traffic). |
| `--iter` | `int` | `5` | Number of statistical iterations. |

#### Execution & Debug Options
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--debug_pids` | `flag` | `True` | **Packet Tracking (Default On):** Intercepts every packet retirement in BookSim2 and exports `packet_tracking_debug.csv` containing $ctime$, $itime$, $atime$, and flit metrics. |
| `--no_debug_pids` | `flag` | `False` | Disables packet tracking export to reduce disk I/O overhead for long benchmark sweeps. |
| `--parallel` | `flag` | `False` | Enables parallel compute execution for heterogeneous xPU + PIM architectures. |
| `--data_mode` | `str` | `synthesis` | Compute execution mode (`synthesis` for trace-based, `analytical` for Roofline). |

---

## 📊 Trace Analysis & Visualization Suite

### 1. Macroscopic Latency Breakdown & Network Saturation (`analyze_traces.py`)

Parses cycle-accurate `.trc` files and `packet_tracking_debug.csv` across simulation runs, isolating pure GPU compute time from physical network transit and synchronization stalls, and synthesizing the network saturation curve.

```bash
cd LLMSimulator

# Analyze the 3 most recent simulations (generates latency anatomy, MoE breakdown, and saturation curve)
python3 analyze_traces.py --recent 3

# Filter specifically by the Mixtral model
python3 analyze_traces.py --model mixtral --recent 5

# Force semilogarithmic scale on the Y-axis for high-dispersion network saturation curves
python3 analyze_traces.py --recent 3 --semilog
```

**Generated Visualizations (saved in `build/analysis/analisis_<timestamp>/`):**
* **`anatomia_latencia.png`:** A stacked bar chart breaking down total execution time into GPU Compute, Network Transit (`moe_scatter`/`moe_gather`/`all_reduce`), and Synchronization Stalls (`NETWORK_STALL`).
* **`desglose_primitivas_moe.png`:** A direct comparative bar chart contrasting the network latency of `moe_scatter` versus `moe_gather`.
* **`curva_saturacion_red.png`:** The fundamental Network-on-Chip (NoC) saturation curve (Mean Network Latency vs. Real Injected Offered Load $\lambda$ in flits/cycle/node). Features:
  * **Real Injected Load ($\lambda$, X-Axis):** Measured in flits/cycle/node as $\lambda = \frac{\text{Total Flits}}{N_{\text{GPUs}} \times \Delta\text{Cycles}_{\text{collective}}}$.
  * **Network Latency (Y-Axis):** Cycle-accurate `Avg_Flit_Latency` in BookSim2 cycles, with auto-detection of semilogarithmic scaling for wide latency dispersion.
  * **Dual-Level Visualization:** Displays per-layer collective dispersion clouds (light markers) alongside prominent macro-operating points labeled with topology, Virtual Channels (VCs), batch size, Tensor Parallelism degree, and skewness factor (e.g. `8dev Torus (VCs=4, BS=32, Skew=0.5)`).
  * **Robust Fallback:** Safely omits the saturation curve if historical result folders lack `packet_tracking_debug.csv` without interrupting latency breakdowns.

---

### 2. Network Congestion Gantt Visualizer (`plot_packet_tracking.py`)

Visualizes the lifecycle of individual packets through the NoC using `packet_tracking_debug.csv` (generated by default).

```bash
cd LLMSimulator

# Default: Paginated Gantt for the last iteration (50 packets per page, up to 30 pages)
python3 plot_packet_tracking.py build/results/<simulation_folder>/

# Custom pagination parameters (e.g. 50 samples per page, all pages)
python3 plot_packet_tracking.py build/results/<simulation_folder>/ --samples 50 --max_pages 0

# Include all simulation iterations (disable automatic last-iteration filtering)
python3 plot_packet_tracking.py build/results/<simulation_folder>/ --all_iters
```

**Key Features & Visual Output:**
* **Dual X-Axis (BookSim2 Cycles & Global LLM Nanoseconds):**
  * **Primary Bottom X-Axis:** BookSim2 network simulation cycles ($ctime \to itime \to atime$).
  * **Secondary Top X-Axis:** Global LLM Simulator Clock ($Global\_NS = Op\_Start\_NS + (Cycle - Op\_Start\_Cycle)$), establishing complete temporal congruence with the GPU cycle-to-cycle chronogram.
* **Automated Last-Iteration Filtering:** Automatically detects simulation iterations by tracking decreases in `Op_Start_NS`, isolating the steady-state final iteration by default (use `--all_iters` to inspect every iteration).
* **Paginated Output (`gantt/` Subdirectory):**
  * Generates sequential high-definition plots `gantt/gantt_page_XXX_pids_X_to_Y.png` partitioned into chunks of 50 packets (`--samples 50`).
  * Supports `--max_pages <N>` (default `30`, or `0` for all pages) to keep visualization generation fast and manageable even with hundreds of thousands of packets.
* **Dual-Segment Horizontal Bars:**
  * 🟧 **NIC Queueing Delay:** Time spent waiting in the network interface injection buffer ($itime - ctime$). Highlights injection buffer saturation.
  * 🟦 **NoC Flight Time:** Time spent actively traversing network routers and channels ($atime - itime$). Reflects physical link contention and buffer arbitrations.
* **Enriched Flit-Level Metric Labels:**
  * Every bar displays routing, wire size, average flit latency, cumulative network productivity, and global LLM nanosecond timestamps:
    `S{src}→D{dst} (9 flits / 288B) | Lat.Media: {avg_flit_lat:.1f}c | Prod: {prod:.3f} flits/c | NS: {g_start}-{g_end}`
* **Network Operation Shading & Badges:**
  * Alternating soft background bands (`ax.axhspan`) differentiate consecutive operations (light blue for `Scatter`, light purple for `Gather`, soft lavender `#ede7f6` for `AllReduce`).
  * Dashed dividing lines separate distinct operations cleanly.
  * Operation badges positioned on the right-hand margin identify the collective operation and absolute GPU timeline window: e.g. `Scatter Nº1 \n NS 6362 - 10547` or `AllReduce Nº1 \n NS 3730 - 4895`.
* **Three Congestion Landmarks:**
  * **`gantt_1_fase_libre.png` (Free Phase):** Initial packets traversing an uncongested network (zero queueing, minimal flight latency).
  * **`gantt_2_congestion_media.png` (Moderate Congestion):** Window centered around the first packets exceeding 1,500 clock cycles, showing the characteristic staircase pattern of queue buildup.
  * **`gantt_3_congestion_critica.png` (Critical Bottleneck):** Window centered around packets taking over 2,000 cycles, showcasing structural saturation during massive All-to-All MoE bursts.

---

### 3. Cycle-to-Cycle GPU Chronogram (`plot_cronograma.py`)

Renders a global micro-architectural execution timeline across all GPUs simultaneously, validating Bulk Synchronous Parallel (BSP) synchronization and strict physical causality.

```bash
cd LLMSimulator

# High-resolution 10,000 ns windows (ideal for inspecting individual micro-operations)
python3 plot_cronograma.py build/results/<simulation_folder>/ --window 10000

# Overview 100,000 ns windows (ideal for full transformer layers)
python3 plot_cronograma.py build/results/<simulation_folder>/ --window 100000
```

**Key Features & Visual Output:**
* Plots are saved sequentially inside the `cycle-to-cycle/` subdirectory (`timeline_part_XXX_...png`).
* **Strict Transformer Layer Isolation:**
  * Extracts the decoder layer index (`MoE_decoder_X` / `decoder_X`) and strictly forbids coalescing operations across consecutive layers, creating crisp vertical boundary markers between layers.
* **Multi-Line Adaptive Information per Compute Block:**
  * **Line 1 (Header):** Explicit layer index and macro-operation (e.g. `Layer 0 | Calc: Attention` or `Layer 0 | Calc: ExpertFFN`).
  * **Line 2 (Sequence in Bold):** Ordered list of elementary operations executed within the block, such as `(LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)` in Attention, or `(Exp#0: Gate_Proj + SiLU + Up_Proj + Down_Proj)` in ExpertFFN. For configurations with fewer GPUs than experts ($N_{\text{GPUs}} < E$, e.g. 4 GPUs running Mixtral), it clearly designates multi-expert sequential execution: `(Exp#0,1: 2x[Gate+SiLU+Up+Down])`.
  * **Line 3 (Bottleneck Diagnosis):** Quantifies micro-architectural intensity from `.trc` accumulators (`Comp_ns` vs. `Mem_ns`): `Dur: 22.1us (Mem-Bound 99.8%)`.
* **Physical Internal Sub-divisions:**
  * Draws semi-transparent dashed white vertical lines (`alpha=0.6, linestyle='--'`) at the exact completion timestamps (`END_NS`) of each micro-operation, highlighting the relative duration of steps (e.g. `AttnGen` or `down_proj`) without breaking visual continuity.
* **Individualized Per-GPU Network Metrics (Local MoE Imbalance):**
  * Blue network blocks (`Scatter` and `Gather`) and purple blocks (`AllReduce`) automatically correlate with `packet_tracking_debug.csv` (isolating the final iteration) and personalize metrics for each specific GPU row $d \in [0, N-1]$:
    * **`Scatter` (Incoming Tokens):** Evaluates incoming packets where $\text{Dest} == d$ ($N_{\text{rx}}[d]$), calculating the mean local packet latency and RX throughput. Highlighting hotspot expert accumulation.
    * **`Gather` (Outgoing Activations):** Evaluates outgoing packets where $\text{Source} == d$ ($N_{\text{tx}}[d]$), revealing the heavier activation emission from congested experts.
    * **`AllReduce` (Tensor Parallelism):** Isolates local packets received and injected by device $d$ within its ring sub-group.
  * Dynamically renders individualized metrics:
    `L{L} | {Op} Nº{k} ({N_local} pkts)`
    `Lat.Media: {lat_local}c | Prod: {prod_local} f/c`
    *(e.g. `L2 | Gather Nº3 (336 pkts) | Lat.Media: 2315.4c | Prod: 0.69 f/c` on hotspot GPU 0 versus `L2 | Gather Nº3 (48 pkts) | Lat.Media: 237.1c | Prod: 0.11 f/c` on GPU 7 under Zipfian skewness $s=1.0$).* If a GPU has no traffic in that collective, it clearly designates `(0 pkts)`.
* **Adaptive Block Duration Formatting & Anti-Overflow Protection:**
  * Automatically calculates the visible temporal width $\Delta t = \text{end\_ns} - \text{start\_ns}$ for each block:
    * **$\Delta t < 800\text{ ns}$:** Text is omitted entirely to prevent visual clutter in narrow residual transitions or micro-stalls.
    * **$800\text{ ns} \le \Delta t < 2{,}000\text{ ns}$ (Ultra-Compact 1-Line):** Displays a concise centered label (e.g., `{Op} Nº{k} ({N_local}p)` or `AR Nº{k} (1.2us)`, `Stall`, `L{L} | {Op}`) at `fontsize=6.5`.
    * **$2{,}000\text{ ns} \le \Delta t < 6{,}000\text{ ns}$ (Compact 2-Line):** Renders up to two compact lines (`fontsize=6.8/6.2`) balancing operation metadata and per-GPU network metrics without crowding.
    * **$\Delta t \ge 6{,}000\text{ ns}$ (Full 3-Line):** Displays complete header, ordered sequence, PIDs range, and micro-architectural diagnostics.
  * **Strict Bounding-Box Clipping (`set_clip_path(rect)`):** Every text label is hard-clipped to its parent rectangle patch (`clip_on=True`), mathematically guaranteeing zero text spill into adjacent blocks.
  * **Top-Margin Legend Padding:** Dynamically expands the upper axis limit to keep the global legend completely above GPU 7 without obscuring execution blocks.
* **Semantic Color Coding:**
  * 🟩 **Green (Calc / Operation):** Productive GPU compute (`POP_OPERATION`).
  * 🟦 **Blue (Scatter / Gather):** MoE Collective network communication serviced by BookSim2.
  * 🟪 **Purple (AllReduce, `#8e44ad`):** Tensor Parallelism Ring-AllReduce network communication serviced by BookSim2.
  * 🟥 **Red (Stall):** Idle GPU time waiting at a global synchronization barrier due to imbalance (`NETWORK_STALL`).
* **Anti-Appends Filter & Global Coalescing:**
  * Trace coalescing is executed globally per GPU prior to windowing, ensuring seamless continuity across 10,000 ns window cuts. Automatically purges stale trace entries if `.trc` files contain concatenated runs.

---

## 🔬 Theoretical Foundation: Packet Sizing & Flit Allocation

In Mixtral 8x7B simulations, all packets uniformly report **9 flits** and **288 Bytes**:

$$\begin{aligned}
\text{Hidden Dimension } (k) &= 4096 \text{ Bytes/token} \\
\text{Network MTU} &= 256 \text{ Bytes} \\
\frac{4096\text{ B}}{256\text{ B}} &= 16 \text{ exact packets (remainder } 0)
\end{aligned}$$

Because $4096$ is an exact multiple of the $256\text{ B}$ MTU, no fractional packets are generated:
1. **Packet Payload:** Exactly $256\text{ Bytes}$.
2. **Total Packet Size:** $256\text{ B (payload)} + 24\text{ B (header)} = 280\text{ Bytes}$.
3. **Flits Required:** $\lceil 280 / 32\text{ B/flit} \rceil = \mathbf{9\text{ flits}}$ (8 full flits $+ 1$ tail flit holding the remaining 24 B of payload and 8 B of physical padding).
4. **Physical Wire Footprint:** $9 \times 32\text{ B/flit} = \mathbf{288\text{ Bytes}}$.

---

## 🤝 Credits & Acknowledgments

This Master's Thesis research builds upon two open-source projects:

* **[LLMSimulator](https://github.com/scale-snu/LLMSimulator):** Developed by the SCALE (Software and Computer Architecture Lab) group at Seoul National University (SNU).
* **[BookSim2](https://github.com/booksim/booksim2):** Developed by the Stanford Concurrent VLSI Architecture Group.

*The Oracle co-simulation architecture, C++ integration APIs, queue/flight packet tracking instrumentation, and the complete analysis and visualization toolchain were developed specifically for this Master's Thesis.*