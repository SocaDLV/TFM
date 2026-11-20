# LLM-NoC Co-Simulation Framework

[![C++17](https://img.shields.io/badge/C++-17-blue.svg)](https://en.cppreference.com/w/cpp/17)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![CMake 3.14+](https://img.shields.io/badge/CMake-3.14+-red.svg)](https://cmake.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

An execution-driven, cycle-accurate co-simulation environment designed to evaluate physical interconnection network bottlenecks and microarchitectural scaling in Large Language Models (LLMs), with specialized focus on coarse-grained and fine-grained **Mixture-of-Experts (MoE)** architectures.

The framework integrates the compute- and memory-graph execution modeling of **LLMSimulator** (analytical Roofline compute models and Ramulator 2.0 HBM3/HBM3e subsystems) with the flit-level network simulation fidelity of **BookSim2** through a causally synchronous Bulk Synchronous Parallel (BSP) Oracle.

Supported workloads include dense transformer baselines (LLaMA-3, LLaMA-2) and MoE architectures such as **Mixtral 8x7B** (coarse-grained, Top-2 routing) and **DeepSeek-V3** (fine-grained MoE with Multi-Head Latent Attention [MLA], FP8/BF16 dual precision, 256 routed micro-experts, and local shared experts). The environment models hardware accelerators (**NVIDIA B100**, **B200**, **H100**, **A100**), configurable load skewness (Zipfian token distribution), cycle-accurate Tensor Parallelism (`AllReduce`), and flexible network topologies (**1D Torus/Ring**, **2D Mesh**, **2D Torus**, **3D Mesh**, and asymmetric **AnyNet** graphs).

---

## Key Features

* **Flit-Level Interconnect Fidelity:** Replaces static analytical network equations with BookSim2 flit-by-flit modeling, capturing virtual channel (VC) allocation, credit flow control, Head-of-Line blocking, NIC queueing delays, and physical link contention.
* **Interactive Web GUI (LLM-NoC Co-Simulation Workbench):** Full-featured local web interface providing real-time architectural guardrails, dynamic on-the-fly HTML5 Canvas cronograms and packet tracking (including a synchronized Split-Screen Hybrid Visualizer), multi-simulation comparison, and topological heatmaps.
* **Advanced MoE and Attention Modeling:** Models Grouped-Query Attention (GQA), Multi-Head Latent Attention (MLA with low-rank KV/Query compression), SwiGLU activation modules, expert partitioning across GPUs, and load-imbalance in-cast hotspots.
* **Cycle-Accurate Tensor Parallelism (AllReduce):** Simulates flit-level Ring-AllReduce communication across devices when `tensor_degree > 1`, capturing individual chunk traversal, injection serialization, and synchronization barriers.
* **Independent CLI and Batch Toolchain:** Standalone Python CLI scripts (`run_sim.py`, `analyze_traces.py`, `plot_cronograma.py`, `plot_packet_tracking.py`) running in complete decoupling from the GUI, guaranteeing 100% numerical parity.
* **Microarchitectural Corrections over Base Simulator:** Enforces residual connection integrity, dependency barriers in SwiGLU chains, clean zero-cycle trace initialization, and asynchronous clock advance based on individual destination arrival times.

---

## Repository Structure

```text
.
|-- booksim2/                   # BookSim2 cycle-accurate network simulator source tree
|-- docs/
|   |-- TFM_Technical_Bible.md  # Comprehensive technical, mathematical, and design reference
|   |-- TFM_Technical_Bible.docx # Compiled documentation mirror
|-- LLMSimulator/
|   |-- gui/                    # Web GUI backend (REST API, trace parsers, analysis) and static assets
|   |-- run_gui.sh              # One-click Linux launcher for the interactive web interface
|   |-- launch_gui.py           # Python entry point for the local web server
|   |-- run_sim.py              # CLI automated simulation orchestrator
|   |-- analyze_traces.py       # Macroscopic latency breakdown and network saturation analyzer
|   |-- plot_cronograma.py      # Cycle-accurate GPU cronogram visualizer
|   |-- plot_packet_tracking.py # Flit-level network packet tracking visualizer
|   |-- src/, eval/             # LLMSimulator C++ engine, hardware profiles, and module graphs
|-- requirements.txt            # Python dependencies for CLI and GUI environments
```

---

## Prerequisites and Installation

### Dependencies

* **C++ Compiler:** GCC 9.0+ or Clang with C++17 support (`g++`, `clang++`).
* **Build System:** CMake 3.14+ and Make.
* **Python Environment:** Python 3.9+ with standard scientific libraries.

### Build Instructions

```bash
# 1. Clone the repository
git clone https://github.com/SocaDLV/TFM.git
cd TFM

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Compile the Co-Simulator (LLMSimulator core and BookSim2 library)
cd LLMSimulator
cmake -B build
cmake --build build -j$(nproc)
cd ..
```

The build process automatically generates the unified co-simulation binary at `LLMSimulator/build/run`.

---

## Usage

### 1. Interactive Web GUI (Recommended)

The **LLM-NoC Co-Simulation Workbench** provides an integrated visual environment to configure, execute, monitor, and analyze simulations without generating static image files.

```bash
cd LLMSimulator
./run_gui.sh
```

The launcher performs automatic environment verification, validates compiler binaries, purges temporary staging residues, and opens `http://127.0.0.1:8080` in your default browser. It supports arguments such as `--port <PORT>` and `--no-browser`.

#### Workbench Tabs

* **Tab 1 — Interactive Configurator & Live Console:** Parameter inputs with live microarchitectural guardrails (preventing Torus routing deadlocks, partition errors, and invalid expert assignments) alongside a real-time streaming execution console.
* **Tab 2 — Results & Interactive Timelines:** On-the-fly HTML5 Canvas rendering of the cycle-accurate GPU Cronogram and NoC Packets in Flight. Includes selective staging persistence, instant unit toggling (Clock Cycles vs. Absolute Time), iteration filtering, and a synchronized **Hybrid Split-Screen Visualizer** (left: GPU Cronogram; right: NoC Packets) with virtual scrolling and cross-inspection tooltips.
* **Tab 3 — History Manager & Multi-Simulation Comparator:** Catalog of saved benchmarks with tagging and deletion. Enables multi-run selection to generate unified comparative metric tables and three automated scientific plots: *Macro Latency Anatomy*, *Collective Primitives Breakdown*, and *Network Saturation Curve* (with optional semilogarithmic scaling).
* **Tab 4 — NoC Topology Map, Traffic Heatmap & Architectural Inspector:** Vector layouts for 1D Torus (radial circular layout with 1c neighbor links and 2c wrap-around arcs), 2D Mesh/Torus (AnyNet orthogonal grid), and 3D Mesh. Displays 4-stage continuous thermal heatmaps on nodes and physical links, directional flow arrows ($Src \to Dst$), geometric hit-testing with interactive hover cards, and structural comparisons between Mixtral 8x7B, DeepSeek-V3, and LLaMA.

### 2. Standalone CLI Workflow

For automated batch sweeps and headless cluster environments, simulations and post-processing tools can be invoked directly from the terminal:

```bash
cd LLMSimulator

# Run a Mixtral 8x7B simulation on an 8-GPU 1D Torus topology
python3 run_sim.py --model mixtral --topology torus --net_dims 8 --vcs 4 --batch_size 32

# Run an asymmetric 2D Mesh (4x2 = 8 GPUs) with Tensor Parallelism (TP=2)
python3 run_sim.py --model mixtral --topology mesh --net_dims 4 2 --tensor_degree 2 --batch_size 32

# Compare the 3 most recent simulations and generate publication-quality figures
python3 analyze_traces.py --recent 3 --semilog

# Generate standalone timeline plots from a simulation directory
python3 plot_cronograma.py --dir build/results/<simulation_folder> --all_iterations
python3 plot_packet_tracking.py --csv build/results/<simulation_folder>/packet_tracking_debug.csv --regime critical
```

The CLI toolchain operates completely decoupled from the web interface while sharing identical mathematical and trace-parsing logic.

---

## Technical Documentation

A comprehensive architectural, mathematical, and design reference is maintained in the repository:

* **[TFM Technical Bible (`docs/TFM_Technical_Bible.md`)](file:///home/igilolt/Escritorio/TFM/docs/TFM_Technical_Bible.md):** 10 chapters covering base simulator execution flow, mathematical formulations for Mixtral and DeepSeek-V3, BookSim2 internal pipeline and packet lifecycle, Oracle synchronization mechanisms, causal barrier audits, trace logging architectures, numerical parity validations, and technical defense defense questions.
* A precompiled Word mirror is available at `docs/TFM_Technical_Bible.docx`.

---

## Author, Credits & Acknowledgments

* **Author:** SocaDLV — Master's Thesis (*Trabajo de Fin de Máster*, TFM), Master's Degree in Computer and Network Engineering, Universitat Politècnica de València (UPV).
* **Repository:** [https://github.com/SocaDLV/TFM](https://github.com/SocaDLV/TFM)

### Base Frameworks

* **LLMSimulator:** Developed by the SCALE (Software and Computer Architecture Lab) group at Seoul National University (SNU). Reference: *Duplex: A High-Fidelity Simulation Framework for LLM Inference Serving Systems*, IEEE/ACM International Symposium on Microarchitecture (MICRO), 2024. [https://github.com/scale-snu/LLMSimulator](https://github.com/scale-snu/LLMSimulator)
* **BookSim2:** Developed by the Stanford Concurrent VLSI Architecture Group. [https://github.com/booksim/booksim2](https://github.com/booksim/booksim2)

*The closed-loop Oracle co-simulation architecture, cycle-accurate Tensor Parallelism AllReduce integration, DeepSeek-V3 fine-grained MoE + MLA implementation, flit-level packet lifecycle tracking instrumentation, interactive Web GUI (LLM-NoC Co-Simulation Workbench), and visualization toolchain were designed and implemented specifically for this Master's Thesis.*
