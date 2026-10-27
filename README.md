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
* **Flit-Level Packet Lifecycle & Network Throughput Tracking (`--debug_pids`):**
  * High-precision temporal tracking of every retired packet:
    * **`Creation_Cycle` ($ctime$):** Cycle at which the MoE communication layer generates the packet burst.
    * **`Inject_Cycle` ($itime$):** Cycle at which the head flit leaves the network interface controller (NIC) queue and enters the first router.
    * **`Receive_Cycle` ($atime$):** Cycle at which the tail flit is retired at the destination GPU.
  * Rigorous decomposition of total packet latency into **NIC Queueing Delay** ($itime - ctime$) and **NoC Flight Time** ($atime - itime$).
  * **Flit-Level Network Productivity & Latency Metrics:**
    * **Average Flit Latency (`Avg_Flit_Latency`):** Exact mean cycle latency across all individual flits composing the packet:
      $$\text{Avg\_Flit\_Latency} = \frac{\sum_{i=1}^{N_{\text{flits}}} (t_{\text{retire}, i} - ctime)}{N_{\text{flits}}}$$
    * **Network Throughput (`Throughput`):** Cumulative flit retirement productivity up to that cycle:
      $$\text{Throughput} = \frac{\sum \text{Flits Received}}{\Delta \text{Cycles Simulated}} \quad [\text{flits/cycle}]$$
  * **LLM Network Operation Context & Temporal Boundaries:**
    * Automatic attribution of each packet to its LLM collective operation: `Op_Type` (`Scatter` or `Gather`), `Op_Idx` (correlative counter per iteration, reset upon clock drop), and absolute GPU chronogram window `Op_Start_NS` and `Op_End_NS`.
  * Comprehensive logging of Packet ID (`PID`), routing tuple (`Source`, `Dest`), flit count (`Num_Flits`), and physical wire footprint (`Size_Bytes`).
* **Micro-Architectural Hierarchical Tracing:**
  * Propagation of the full C++ module namespace (`module_map_name`) into `.trc` event logs. This disambiguates generic compute entries (`Calc`) into specific operations: **ExpertFFN** (`gate_proj`, `up_proj`, `down_proj`, activations), **Attention** (QKV projections, self-attention, `o_proj`), **Linear**, **LayerNorm**, **Residual**, etc.
* **Rigorous Packetization Modeling:**
  * Precise segmentation into Maximum Transmission Units ($\text{MTU} = 256\text{ B}$), headers ($\text{Header} = 24\text{ B}$), and flits ($\text{Flit Size} = 32\text{ B}$).
  * Exact physical wire modeling: activation vectors of $4096\text{ B}$ (Mixtral) partition into exactly 16 packets with $256\text{ B}$ payload $+ 24\text{ B}$ header $= 280\text{ B}$, requiring $\lceil 280 / 32 \rceil = 9\text{ flits}$ ($288\text{ B}$ physically transferred over the wire).
* **Architectural Corrections & Simulator Stability:**
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

# Example 1: 1D Torus Topology (8 GPUs) with Batch Size 32
python3 run_sim.py --model mixtral --net_dims 8 --topology torus --vcs 4 --batch_size 32

# Example 2: 2D Mesh Topology (4x4 = 16 GPUs)
python3 run_sim.py --model mixtral --net_dims 4 4 --topology mesh --vcs 4

# Example 3: Packet Debug Mode (Generates packet_tracking_debug.csv)
python3 run_sim.py --model mixtral --net_dims 8 --topology torus --vcs 2 --batch_size 32 --iter 1 --output_len 2 --debug_pids
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
| `--input_len` | `int` | `1024` | Prompt length (prefill tokens). |
| `--output_len` | `int` | `10` | Tokens to generate per iteration (drives sustained MoE traffic). |
| `--iter` | `int` | `5` | Number of statistical iterations. |

#### Execution & Debug Options
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--debug_pids` | `flag` | `False` | **Packet Tracking:** Intercepts every packet retirement in BookSim2 and exports `packet_tracking_debug.csv` containing $ctime$, $itime$, and $atime$. |
| `--parallel` | `flag` | `False` | Enables parallel compute execution for heterogeneous xPU + PIM architectures. |
| `--data_mode` | `str` | `synthesis` | Compute execution mode (`synthesis` for trace-based, `analytical` for Roofline). |

---

## 📊 Trace Analysis & Visualization Suite

### 1. Macroscopic Latency Breakdown (`analyze_traces.py`)

Parses cycle-accurate `.trc` files across simulation runs and isolates pure GPU compute time from physical network transit and synchronization stalls.

```bash
cd LLMSimulator

# Analyze the 3 most recent simulations
python3 analyze_traces.py --recent 3

# Filter specifically by the Mixtral model
python3 analyze_traces.py --model mixtral --recent 5
```

**Generated Visualizations (saved in `build/analysis/analisis_<timestamp>/`):**
* **`anatomia_latencia.png`:** A stacked bar chart breaking down total execution time into GPU Compute, Network Transit (`moe_scatter`/`moe_gather`), and Synchronization Stalls (`NETWORK_STALL`).
* **`desglose_primitivas_moe.png`:** A direct comparative bar chart contrasting the network latency of `moe_scatter` versus `moe_gather`.

---

### 2. Network Congestion Gantt Visualizer (`plot_packet_tracking.py`)

Visualizes the lifecycle of individual packets through the NoC using `packet_tracking_debug.csv` (requires running the simulation with `--debug_pids`).

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
* **Automated Last-Iteration Filtering:** Automatically detects simulation iterations by tracking decreases in `Op_Start_NS`, isolating the steady-state final iteration by default (use `--all_iters` to inspect every iteration).
* **Paginated Output (`gantt/` Subdirectory):**
  * Generates sequential high-definition plots `gantt/gantt_page_XXX_pids_X_to_Y.png` partitioned into chunks of 50 packets (`--samples 50`).
  * Supports `--max_pages <N>` (default `30`, or `0` for all pages) to keep visualization generation fast and manageable even with hundreds of thousands of packets.
* **Dual-Segment Horizontal Bars:**
  * 🟧 **NIC Queueing Delay:** Time spent waiting in the network interface injection buffer ($itime - ctime$). Highlights injection buffer saturation.
  * 🟦 **NoC Flight Time:** Time spent actively traversing network routers and channels ($atime - itime$). Reflects physical link contention and buffer arbitrations.
* **Enriched Flit-Level Metric Labels:**
  * Every bar displays routing, wire size, average flit latency, and cumulative network productivity:
    `S{src}→D{dst} (9 flits / 288B) | Lat.Mitja: {avg_flit_lat:.1f}c | Prod: {prod:.3f} flits/c`
* **Network Operation Shading & Badges:**
  * Alternating soft background bands (`ax.axhspan`) differentiate consecutive operations (light blue for `Scatter`, light purple for `Gather`).
  * Dashed dividing lines separate distinct operations cleanly.
  * Operation badges positioned on the right-hand margin identify the collective operation and absolute GPU timeline window: e.g. `Scatter Nº1 \n NS 6362 - 10547`.
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
* **Dual-Label Compute Rendering:**
  * Green compute boxes display `"Calc"` in the upper half and the specific operation name (**ExpertFFN**, **Attention**, **Linear**, etc.) in **bold** directly below it.
* **Intelligent Algorithmic Coalescing:**
  * Contiguous micro-operations of the same logical stage (e.g., `gate_proj`, `activation`, `up_proj`, `down_proj`) are automatically unified into a single seamless **ExpertFFN** box.
* **Semantic Color Coding:**
  * 🟩 **Green (Calc / Operation):** Productive GPU compute (`POP_OPERATION`).
  * 🟦 **Blue (Scatter / Gather):** Network communication serviced by BookSim2.
  * 🟥 **Red (Stall):** Idle GPU time waiting at a global synchronization barrier due to imbalance (`NETWORK_STALL`).
* **Anti-Appends Filter:** Automatically detects and purges stale trace entries if `.trc` files were previously concatenated or reused across simulation runs.

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