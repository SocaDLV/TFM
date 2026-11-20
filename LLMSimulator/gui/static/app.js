/**
 * LLM-NoC Co-Simulation Workbench - Interactive Frontend Controller
 * Manages tab switching, real-time guardrail validation, dynamic previews,
 * simulation execution, live console polling, and help/credits modal.
 */

document.addEventListener("DOMContentLoaded", () => {
  // =========================================================================
  // State Variables
  // =========================================================================
  let isSimulating = false;
  let pollingInterval = null;
  let logOffset = 0;
  let timerInterval = null;
  let elapsedTimerSeconds = 0;
  let currentStagingFolder = null;

  // =========================================================================
  // DOM Elements Selection
  // =========================================================================
  // Navigation
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const tab2Badge = document.getElementById("tab2-badge");

  // Status & Header
  const liveStatusPill = document.getElementById("live-status-pill");
  const liveStatusText = document.getElementById("live-status-text");
  const btnOpenHelp = document.getElementById("btn-open-help");
  const helpModal = document.getElementById("help-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnModalOk = document.getElementById("btn-modal-ok");

  // Tab 1 Form Controls
  const cfgModel = document.getElementById("cfg-model");
  const modelDescBox = document.getElementById("model-desc-box");
  const cfgGpu = document.getElementById("cfg-gpu");
  const cfgDataMode = document.getElementById("cfg-data-mode");
  const cfgBatchSize = document.getElementById("cfg-batch-size");
  const cfgInputLen = document.getElementById("cfg-input-len");
  const cfgOutputLen = document.getElementById("cfg-output-len");
  const cfgIter = document.getElementById("cfg-iter");
  const cfgTp = document.getElementById("cfg-tp");
  const cfgSkewnessSlider = document.getElementById("cfg-skewness-slider");
  const cfgSkewnessInput = document.getElementById("cfg-skewness-input");
  const skewnessLabel = document.getElementById("skewness-label");

  const cfgTopology = document.getElementById("cfg-topology");
  const cfgNetDims = document.getElementById("cfg-net-dims");
  const gpuCountPill = document.getElementById("gpu-count-pill");
  const anynetNotePill = document.getElementById("anynet-note-pill");
  const cfgRouting = document.getElementById("cfg-routing");
  const cfgVcs = document.getElementById("cfg-vcs");
  const cfgDebugPids = document.getElementById("cfg-debug-pids");

  // Guardrails & Bottom Panel
  const guardrailsContainer = document.getElementById("guardrails-container");
  const cmdPreviewText = document.getElementById("cmd-preview-text");
  const btnCopyCmd = document.getElementById("btn-copy-cmd");
  const btnRunSim = document.getElementById("btn-run-sim");
  const btnAbortSim = document.getElementById("btn-abort-sim");
  const execTimer = document.getElementById("exec-timer");
  const execProgressTag = document.getElementById("exec-progress-tag");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const progressDetailText = document.getElementById("progress-detail-text");
  const consoleOutput = document.getElementById("console-output");
  const chkAutoscroll = document.getElementById("chk-autoscroll");
  const btnClearConsole = document.getElementById("btn-clear-console");
  const completionToast = document.getElementById("completion-toast");
  const btnJumpResults = document.getElementById("btn-jump-results");

  // Tab 2 Elements
  const stagingBanner = document.getElementById("staging-banner");
  const stagingBadgePill = document.getElementById("staging-badge-pill");
  const stagingFolderName = document.getElementById("staging-folder-name");
  const stagingSaveStatus = document.getElementById("staging-save-status");
  const iterationSelector = document.getElementById("iteration-selector");
  const btnUnitCycles = document.getElementById("btn-unit-cycles");
  const btnUnitTime = document.getElementById("btn-unit-time");
  const stagingCustomLabel = document.getElementById("staging-custom-label");
  const btnSaveStaging = document.getElementById("btn-save-staging");
  const btnDiscardStaging = document.getElementById("btn-discard-staging");

  // Tab 2 KPIs
  const kpiWallclock = document.getElementById("kpi-wallclock");
  const kpiCompute = document.getElementById("kpi-compute");
  const kpiComputeSub = document.getElementById("kpi-compute-sub");
  const kpiTransit = document.getElementById("kpi-transit");
  const kpiTransitSub = document.getElementById("kpi-transit-sub");
  const kpiStalls = document.getElementById("kpi-stalls");
  const kpiStallsSub = document.getElementById("kpi-stalls-sub");
  const kpiLambda = document.getElementById("kpi-lambda");
  const kpiFlitLat = document.getElementById("kpi-flit-lat");
  const kpiTotalPkts = document.getElementById("kpi-total-pkts");
  const kpiTotalFlitsSub = document.getElementById("kpi-total-flits-sub");

  // Tab 2 Subviews & Canvases
  const btnSubviewChrono = document.getElementById("btn-subview-chrono");
  const btnSubviewPackets = document.getElementById("btn-subview-packets");
  const btnSubviewHybrid = document.getElementById("btn-subview-hybrid");
  const subviewChronoContainer = document.getElementById("subview-chrono-container");
  const subviewPacketsContainer = document.getElementById("subview-packets-container");
  const subviewHybridContainer = document.getElementById("subview-hybrid-container");

  // Chronogram Controls
  const presetButtons = document.querySelectorAll(".btn-preset");
  const btnChronoZoomIn = document.getElementById("btn-chrono-zoom-in");
  const btnChronoZoomOut = document.getElementById("btn-chrono-zoom-out");
  const btnChronoZoomReset = document.getElementById("btn-chrono-zoom-reset");
  const chronoWindowInfo = document.getElementById("chrono-window-info");
  const chronogramCanvasEl = document.getElementById("chronogram-canvas");
  const chronogramTooltipEl = document.getElementById("chronogram-tooltip");
  const chronogramScrubber = document.getElementById("chronogram-scrubber");
  const chronoScrubberPos = document.getElementById("chrono-scrubber-pos");

  // Packet Flight Controls
  const btnRegimeFree = document.getElementById("btn-regime-free");
  const btnRegimeMedium = document.getElementById("btn-regime-medium");
  const btnRegimeCritical = document.getElementById("btn-regime-critical");
  const packetsLimitSelect = document.getElementById("packets-limit-select");
  const packetsPageInfo = document.getElementById("packets-page-info");
  const packetsCanvasEl = document.getElementById("packets-canvas");
  const packetsTooltipEl = document.getElementById("packets-tooltip");
  const packetsScrubber = document.getElementById("packets-scrubber");
  const packetsScrubberPos = document.getElementById("packets-scrubber-pos");

  // Hybrid Split-Screen Controls
  const hybridPresetButtons = document.querySelectorAll(".btn-hybrid-preset");
  const btnHybridZoomIn = document.getElementById("btn-hybrid-zoom-in");
  const btnHybridZoomOut = document.getElementById("btn-hybrid-zoom-out");
  const btnHybridZoomReset = document.getElementById("btn-hybrid-zoom-reset");
  const hybridWindowInfo = document.getElementById("hybrid-window-info");
  const hybridPacketBadge = document.getElementById("hybrid-packet-badge");
  const hybridChronogramCanvasEl = document.getElementById("hybrid-chronogram-canvas");
  const hybridPacketsCanvasEl = document.getElementById("hybrid-packets-canvas");
  const hybridTooltipEl = document.getElementById("hybrid-tooltip");
  const hybridScrubber = document.getElementById("hybrid-scrubber");
  const hybridScrubberPos = document.getElementById("hybrid-scrubber-pos");

  // Tab 2 State & Controllers
  let chronoCanvas = null;
  let packetFlightCanvas = null;
  let hybridSyncController = null;
  let currentResultsSource = "staging";
  let packetsOffset = 0;
  let packetsLimit = 100;
  let packetsTotalCount = 0;
  let activeIteration = "last";
  let activeSubview = "chrono";
  let lastChronoData = null;
  let lastSummaryData = null;
  let currentSimUnit = "cycles";
  window.activeSimUnit = "cycles";

  // =========================================================================
  // Model Descriptions Database
  // =========================================================================
  const modelDescriptions = {
    mixtral: `
      <span class="model-desc-badge">Sparse MoE</span>
      <strong>Mixtral 8x7B:</strong> 8 expertos enrutados por capa, Top-2 Gating, 32 capas MoE,
      atención GQA (32 heads Q, 8 heads KV, d_head=128), dimensión oculta 4096, precisión FP16.
    `,
    deepseekV3: `
      <span class="model-desc-badge">Fine-Grained MoE</span>
      <strong>DeepSeek-V3:</strong> 256 micro-expertos enrutados + 1 compartido, Top-8 Gating,
      60 capas (3 densas + 57 MoE), Multi-Head Latent Attention (MLA: compresión KV d_c=512),
      precisión mixta FP8 (Scatter) / BF16 (Gather).
    `,
    llama: `
      <span class="model-desc-badge">Dense LLM</span>
      <strong>LLaMA Dense Baseline:</strong> Red densa estándar sin capas dispersas, 32 capas
      decodificadoras densas, atención MHA/GQA, dimensión oculta 4096.
    `
  };

  // =========================================================================
  // Tab Navigation Handling
  // =========================================================================
  function switchTab(targetTabId) {
    tabButtons.forEach(btn => {
      if (btn.getAttribute("data-tab") === targetTabId) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    tabPanes.forEach(pane => {
      if (pane.id === targetTabId) {
        pane.classList.add("active");
      } else {
        pane.classList.remove("active");
      }
    });

    if (targetTabId === "tab-results") {
      ensureResultsLoaded();
      setTimeout(() => {
        if (!subviewChronoContainer.classList.contains("hidden") && chronoCanvas) {
          chronoCanvas.render();
        } else if (!subviewPacketsContainer.classList.contains("hidden") && packetFlightCanvas) {
          packetFlightCanvas.render();
        } else if (!subviewHybridContainer.classList.contains("hidden") && hybridSyncController) {
          hybridSyncController.render();
        }
      }, 50);
    } else if (targetTabId === "tab-history") {
      loadHistoryList();
    }
  }

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      switchTab(targetId);
    });
  });

  btnJumpResults.addEventListener("click", () => {
    switchTab("tab-results");
  });

  // =========================================================================
  // Help & Credits Modal Handling
  // =========================================================================
  btnOpenHelp.addEventListener("click", () => {
    helpModal.classList.remove("hidden");
  });

  const closeModal = () => {
    helpModal.classList.add("hidden");
  };

  btnCloseModal.addEventListener("click", closeModal);
  btnModalOk.addEventListener("click", closeModal);
  helpModal.addEventListener("click", (e) => {
    if (e.target === helpModal) closeModal();
  });

  // =========================================================================
  // Form State & Live Validation (Guardrails)
  // =========================================================================
  function parseNetDims(str) {
    const numbers = str.trim().split(/\s+/).map(Number).filter(n => !isNaN(n) && n > 0);
    return numbers.length > 0 ? numbers : [8];
  }

  function updateDynamicControls() {
    // 1. Update Model Description
    const selectedModel = cfgModel.value;
    modelDescBox.innerHTML = modelDescriptions[selectedModel] || "";

    // 2. Parse Network Dimensions
    const dims = parseNetDims(cfgNetDims.value);
    const totalGpus = dims.reduce((acc, v) => acc * v, 1);
    gpuCountPill.textContent = `${totalGpus} GPU${totalGpus !== 1 ? 's' : ''} en total`;

    // 3. Asymmetric Mesh Check (AnyNet)
    const topology = cfgTopology.value;
    const isAsymMesh = topology === "mesh" && dims.length === 2 && dims[0] !== dims[1];
    if (isAsymMesh) {
      anynetNotePill.classList.remove("hidden");
      anynetNotePill.textContent = `AnyNet 2D (${dims[0]}x${dims[1]})`;
      // Suggest/enforce 'min' for AnyNet
      if (cfgRouting.value !== "min") {
        cfgRouting.value = "min";
      }
    } else {
      anynetNotePill.classList.add("hidden");
      if (cfgRouting.value === "min" && topology !== "mesh") {
        cfgRouting.value = "dim_order";
      }
    }

    // 4. Skewness Label Sync
    const skewVal = parseFloat(cfgSkewnessSlider.value);
    cfgSkewnessInput.value = skewVal.toFixed(1);
    if (skewVal === 0.0) {
      skewnessLabel.textContent = "0.0 (Distribución Uniforme de Tokens)";
    } else {
      skewnessLabel.textContent = `${skewVal.toFixed(1)} (Distribución Zipfiana / Hotspots MoE)`;
    }

    // 5. Evaluate Guardrails
    const vcs = parseInt(cfgVcs.value, 10) || 1;
    const tp = parseInt(cfgTp.value, 10) || 1;
    const batchSize = parseInt(cfgBatchSize.value, 10) || 1;
    const inputLen = parseInt(cfgInputLen.value, 10) || 1024;
    const outputLen = parseInt(cfgOutputLen.value, 10) || 2;
    const iter = parseInt(cfgIter.value, 10) || 2;

    const blockingErrors = [];
    const warnings = [];

    // Blocking Error 1: Torus Deadlock
    if (topology === "torus" && vcs < 2) {
      blockingErrors.push({
        title: "Riesgo de Deadlock Microarquitectural",
        message: "La topología Toro con enrutamiento Dateline exige obligatoriamente al menos 2 canales virtuales (vcs >= 2) para romper ciclos cerrados en el Grafo de Dependencia de Canales (CDG)."
      });
    }

    // Blocking Error 2: Asymmetric topology limit
    if (!dims.every(d => d === dims[0])) {
      if (!(topology === "mesh" && dims.length === 2)) {
        blockingErrors.push({
          title: "Topología Asimétrica No Soportada",
          message: `BookSim2 solo soporta dimensiones regulares simétricas (k^n) o mallas 2D asimétricas mediante AnyNet. ${dims.join("x")} no es admisible para '${topology}'.`
        });
      }
    }

    // Blocking Error 3: Tensor Parallelism Divisibility
    if (totalGpus % tp !== 0) {
      blockingErrors.push({
        title: "Error de Particionamiento Tensorial",
        message: `El número total de GPUs (${totalGpus}) debe ser divisible de forma exacta por el grado de Tensor Parallelism (${tp}).`
      });
    }

    // Blocking Error 4: Mixtral Max GPUs
    if (selectedModel === "mixtral" && totalGpus > 8) {
      blockingErrors.push({
        title: "Límite de Paralelismo MoE Excedido",
        message: `Mixtral 8x7B contiene exactamente 8 expertos; LLMSimulator no soporta particionar expertos entre más de 8 procesadores (${totalGpus} GPUs configuradas).`
      });
    }

    // Warning 1: High GPU count
    if (totalGpus > 64) {
      warnings.push({
        title: "Advertencia de Escalabilidad",
        message: `Simular ${totalGpus} nodos en BookSim2 incrementará la complejidad de arbitraje crossbar O(Ports²), dilatando el tiempo de ejecución.`
      });
    }

    // Warning 2: High token count
    const totalTokensSimulated = outputLen * iter;
    if (totalTokensSimulated > 50) {
      warnings.push({
        title: "Advertencia de Sobrecarga de Tráfico",
        message: `${outputLen} tokens x ${iter} iteraciones = ${totalTokensSimulated} pasos de decodificación. El trazado ciclo a ciclo generará cientos de miles de eventos de red.`
      });
    }

    // Render Guardrails
    renderGuardrails(blockingErrors, warnings);

    // Update Button State
    if (blockingErrors.length > 0 || isSimulating) {
      btnRunSim.disabled = true;
    } else {
      btnRunSim.disabled = false;
    }

    // 6. Update CLI Command Preview
    const dimsStr = dims.join(" ");
    const tpArg = tp > 1 ? ` --tp ${tp}` : "";
    const skewArg = skewVal > 0.0 ? ` --skewness ${skewVal.toFixed(1)}` : "";
    const pidsArg = cfgDebugPids.checked ? "" : " --no_debug_pids";
    const dataModeArg = cfgDataMode.value !== "synthesis" ? ` --data_mode ${cfgDataMode.value}` : "";

    const cmdStr = `python run_sim.py --model ${selectedModel} --net_dims ${dimsStr} --topology ${topology} --vcs ${vcs} --routing ${cfgRouting.value} --batch_size ${batchSize} --input_len ${inputLen} --output_len ${outputLen} --iter ${iter}${tpArg}${skewArg}${dataModeArg}${pidsArg}`;
    cmdPreviewText.textContent = cmdStr;
  }

  function renderGuardrails(errors, warnings) {
    if (errors.length === 0 && warnings.length === 0) {
      guardrailsContainer.innerHTML = "";
      return;
    }

    let html = "";
    errors.forEach(err => {
      html += `
        <div class="guardrail-alert guardrail-danger">
          <span class="guardrail-icon">🛑</span>
          <div class="guardrail-content">
            <strong>${err.title}</strong>
            <p>${err.message}</p>
          </div>
        </div>
      `;
    });

    warnings.forEach(warn => {
      html += `
        <div class="guardrail-alert guardrail-warning">
          <span class="guardrail-icon">⚠️</span>
          <div class="guardrail-content">
            <strong>${warn.title}</strong>
            <p>${warn.message}</p>
          </div>
        </div>
      `;
    });

    guardrailsContainer.innerHTML = html;
  }

  // =========================================================================
  // Event Listeners for Form Controls
  // =========================================================================
  const formInputs = [
    cfgModel, cfgGpu, cfgDataMode, cfgBatchSize, cfgInputLen, cfgOutputLen,
    cfgIter, cfgTp, cfgTopology, cfgNetDims, cfgRouting, cfgVcs, cfgDebugPids
  ];

  formInputs.forEach(input => {
    input.addEventListener("input", updateDynamicControls);
    input.addEventListener("change", updateDynamicControls);
  });

  cfgSkewnessSlider.addEventListener("input", () => {
    cfgSkewnessInput.value = cfgSkewnessSlider.value;
    updateDynamicControls();
  });

  cfgSkewnessInput.addEventListener("input", () => {
    let val = parseFloat(cfgSkewnessInput.value);
    if (isNaN(val)) val = 0.0;
    val = Math.max(0.0, Math.min(2.0, val));
    cfgSkewnessSlider.value = val;
    updateDynamicControls();
  });

  // Copy CLI command button
  btnCopyCmd.addEventListener("click", () => {
    const text = cmdPreviewText.textContent;
    navigator.clipboard.writeText(text).then(() => {
      const orig = btnCopyCmd.textContent;
      btnCopyCmd.textContent = "✅ ¡Copiado!";
      setTimeout(() => { btnCopyCmd.textContent = orig; }, 1500);
    }).catch(err => {
      console.error("Error al copiar comando:", err);
    });
  });

  // Clear console button
  btnClearConsole.addEventListener("click", () => {
    consoleOutput.textContent = "";
  });

  // =========================================================================
  // Status Pill & Timer Management
  // =========================================================================
  function updateLiveStatus(status) {
    liveStatusPill.className = "status-pill";
    switch (status) {
      case "running":
        liveStatusPill.classList.add("status-running");
        liveStatusText.textContent = "Simulando...";
        break;
      case "completed":
        liveStatusPill.classList.add("status-completed");
        liveStatusText.textContent = "Simulación Temporal Lista";
        break;
      case "error":
        liveStatusPill.classList.add("status-error");
        liveStatusText.textContent = "Error en Ejecución";
        break;
      case "aborted":
        liveStatusPill.classList.add("status-aborted");
        liveStatusText.textContent = "Simulación Abortada";
        break;
      default:
        liveStatusPill.classList.add("status-idle");
        liveStatusText.textContent = "Listo";
        break;
    }
  }

  function formatTime(totalSeconds) {
    const sec = Math.floor(totalSeconds % 60);
    const min = Math.floor((totalSeconds / 60) % 60);
    const hrs = Math.floor(totalSeconds / 3600);
    return `⏱️ ${hrs.toString().padStart(2, "0")}:${min.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  }

  function startTimer() {
    elapsedTimerSeconds = 0;
    execTimer.textContent = formatTime(0);
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      elapsedTimerSeconds += 1;
      execTimer.textContent = formatTime(elapsedTimerSeconds);
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timerInterval);
  }

  // =========================================================================
  // Simulation Execution & Polling Controller
  // =========================================================================
  async function launchSimulation() {
    if (isSimulating) return;

    const payload = {
      model: cfgModel.value,
      gpu_gen: cfgGpu.value,
      data_mode: cfgDataMode.value,
      batch_size: parseInt(cfgBatchSize.value, 10),
      input_len: parseInt(cfgInputLen.value, 10),
      output_len: parseInt(cfgOutputLen.value, 10),
      iter: parseInt(cfgIter.value, 10),
      tensor_degree: parseInt(cfgTp.value, 10),
      skewness: parseFloat(cfgSkewnessInput.value),
      topology: cfgTopology.value,
      net_dims: parseNetDims(cfgNetDims.value),
      routing: cfgRouting.value,
      vcs: parseInt(cfgVcs.value, 10),
      debug_pids: cfgDebugPids.checked
    };

    try {
      btnRunSim.disabled = true;
      btnAbortSim.disabled = false;
      isSimulating = true;
      completionToast.classList.add("hidden");
      consoleOutput.textContent = "🚀 Enviando solicitud de co-simulación al backend...\n";
      logOffset = 0;
      updateLiveStatus("running");
      startTimer();

      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }

      consoleOutput.textContent += `📡 Sesión iniciada. Subproceso ./build/run activo.\n`;
      startPolling();

    } catch (err) {
      isSimulating = false;
      stopTimer();
      updateLiveStatus("error");
      btnRunSim.disabled = false;
      btnAbortSim.disabled = true;
      consoleOutput.textContent += `\n❌ Error al lanzar simulación: ${err.message}\n`;
      alert(`Error al iniciar la simulación:\n${err.message}`);
    }
  }

  async function abortSimulation() {
    if (!isSimulating) return;
    btnAbortSim.disabled = true;
    consoleOutput.textContent += `\n🛑 Solicitando cancelación inmediata...\n`;

    try {
      const response = await fetch("/api/abort", { method: "POST" });
      const data = await response.json();
      consoleOutput.textContent += `📡 Estado de aborto: ${data.status}\n`;
    } catch (err) {
      console.error("Error al abortar:", err);
    }
  }

  function startPolling() {
    clearInterval(pollingInterval);
    pollingInterval = setInterval(pollStatus, 500);
  }

  async function pollStatus() {
    try {
      const response = await fetch(`/api/status?offset=${logOffset}`);
      if (!response.ok) return;

      const data = await response.json();

      // Append new log lines
      if (data.logs && data.logs.length > 0) {
        consoleOutput.textContent += data.logs.join("\n") + "\n";
        logOffset = data.log_offset;

        if (chkAutoscroll.checked) {
          consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
      }

      // Update progress bar
      const pct = data.progress_percent || 0;
      progressBarFill.style.width = `${pct}%`;
      execProgressTag.textContent = `Progreso: ${pct}%`;
      progressDetailText.textContent = data.progress_detail || "";

      // Check if simulation ended
      if (data.status !== "running") {
        clearInterval(pollingInterval);
        isSimulating = false;
        stopTimer();
        btnAbortSim.disabled = true;
        btnRunSim.disabled = false;
        updateLiveStatus(data.status);

        if (data.status === "completed") {
          currentStagingFolder = data.staging_folder_name;
          completionToast.classList.remove("hidden");
          tab2Badge.classList.remove("hidden");
          tab2Badge.textContent = "Staging";

          // Preload results for Tab 2
          loadResultsData("staging", currentStagingFolder);
        } else if (data.status === "error") {
          progressDetailText.textContent = data.error_message || "Error en la ejecución";
        }
      }

    } catch (err) {
      console.error("Error en polling /api/status:", err);
    }
  }

  btnRunSim.addEventListener("click", launchSimulation);
  btnAbortSim.addEventListener("click", abortSimulation);

  // =========================================================================
  // Tab 2 Controller: Results, Chronogram & Packet Flight
  // =========================================================================
  function initCanvases() {
    if (typeof ChronogramCanvas !== "undefined" && chronogramCanvasEl) {
      chronoCanvas = new ChronogramCanvas(
        chronogramCanvasEl,
        chronogramTooltipEl,
        (startNs, endNs, minNs, maxNs) => {
          const span = endNs - startNs;
          chronoWindowInfo.textContent = `Ventana: ${formatSimUnit(startNs)} ➔ ${formatSimUnit(endNs)} (${formatSimUnit(span, true)})`;
          chronoScrubberPos.textContent = formatSimUnit(startNs);

          const totalSpan = maxNs - minNs;
          const currentSpan = endNs - startNs;
          const maxStart = maxNs - currentSpan;
          if (maxStart > minNs) {
            const ratio = (startNs - minNs) / (maxStart - minNs);
            chronogramScrubber.value = Math.round(ratio * 1000);
          }
        }
      );
    }

    if (typeof PacketFlightCanvas !== "undefined" && packetsCanvasEl) {
      packetFlightCanvas = new PacketFlightCanvas(
        packetsCanvasEl,
        packetsTooltipEl,
        (offset, limit) => {
          loadPacketsData(currentResultsSource, currentStagingFolder, offset, limit);
        }
      );
    }
  }

  function initHybridController() {
    if (hybridSyncController || typeof HybridSyncController === "undefined") return;
    if (!hybridChronogramCanvasEl || !hybridPacketsCanvasEl) return;

    hybridSyncController = new HybridSyncController({
      chronoCanvasEl: hybridChronogramCanvasEl,
      packetsCanvasEl: hybridPacketsCanvasEl,
      tooltipEl: hybridTooltipEl,
      scrubberEl: hybridScrubber,
      scrubberPosEl: hybridScrubberPos,
      windowInfoEl: hybridWindowInfo,
      packetBadgeEl: hybridPacketBadge,
      fetchPacketsWindowFn: async (startNs, endNs, iter) => {
        if (!currentStagingFolder) return { packets: [], total_in_window: 0 };
        const it = iter || activeIteration;
        try {
          const res = await fetch(`/api/results/packets_window?source=${currentResultsSource}&folder=${currentStagingFolder}&start_ns=${startNs}&end_ns=${endNs}&iteration=${it}&max_packets=0`);
          if (!res.ok) return { packets: [], total_in_window: 0 };
          const data = await res.json();
          if (hybridPacketBadge) {
            const count = data.total_in_window != null ? data.total_in_window : (data.packets ? data.packets.length : 0);
            const trunc = data.truncated ? ` (muestreados ${data.returned || (data.packets ? data.packets.length : 0)})` : "";
            hybridPacketBadge.textContent = `${count.toLocaleString()} paquetes en ventana${trunc}`;
          }
          return data;
        } catch (e) {
          console.error("Error fetching packets_window:", e);
          return { packets: [], total_in_window: 0 };
        }
      },
      onViewportChange: (startNs, endNs, minNs, maxNs) => {
        const span = endNs - startNs;
        if (hybridWindowInfo) {
          hybridWindowInfo.textContent = `Ventana: ${formatSimUnit(startNs)} ➔ ${formatSimUnit(endNs)} (${formatSimUnit(span, true)})`;
        }
        if (hybridScrubberPos) {
          hybridScrubberPos.textContent = formatSimUnit(startNs);
        }
        const currentSpan = endNs - startNs;
        const maxStart = maxNs - currentSpan;
        if (maxStart > minNs && hybridScrubber) {
          const ratio = (startNs - minNs) / (maxStart - minNs);
          hybridScrubber.value = Math.round(ratio * 1000);
        }
      }
    });
  }

  function updateIterationDropdown(numIters) {
    if (!iterationSelector) return;
    const currentVal = iterationSelector.value;
    iterationSelector.innerHTML = "";

    const optLast = document.createElement("option");
    optLast.value = "last";
    optLast.textContent = "Última Iteración (Steady-State)";
    iterationSelector.appendChild(optLast);

    if (numIters > 1) {
      const optAll = document.createElement("option");
      optAll.value = "all";
      optAll.textContent = `Simulación Completa (${numIters} iteraciones)`;
      iterationSelector.appendChild(optAll);

      for (let i = 1; i <= numIters; i++) {
        const opt = document.createElement("option");
        opt.value = String(i);
        let label = `Iteración ${i}`;
        if (i === 1) label += " (Warm-up)";
        else if (i === numIters) label += " (Steady-State)";
        opt.textContent = label;
        iterationSelector.appendChild(opt);
      }
    }

    const exists = Array.from(iterationSelector.options).some(o => o.value === currentVal);
    if (exists) {
      iterationSelector.value = currentVal;
      activeIteration = currentVal;
    } else {
      iterationSelector.value = "last";
      activeIteration = "last";
    }
  }

  async function ensureResultsLoaded() {
    if (!currentStagingFolder) {
      try {
        const res = await fetch("/api/results/active");
        if (res.ok) {
          const act = await res.json();
          if (act.active) {
            currentStagingFolder = act.folder_name;
            currentResultsSource = act.source || "staging";
            loadResultsData(currentResultsSource, currentStagingFolder);
          }
        }
      } catch (e) {
        console.error("Error al consultar simulación activa:", e);
      }
    } else if (chronoCanvas && !chronoCanvas.data) {
      loadResultsData(currentResultsSource, currentStagingFolder);
    }
  }

  async function loadResultsData(source, folder) {
    if (!folder) return;
    currentResultsSource = source;
    currentStagingFolder = folder;

    // Update banner UI
    stagingFolderName.textContent = folder;
    if (source === "saved") {
      stagingBanner.classList.add("saved-mode");
      stagingBadgePill.textContent = "Guardada en Historial";
      stagingBadgePill.className = "staging-badge saved";
      stagingSaveStatus.textContent = "(Guardada)";
      stagingSaveStatus.className = "staging-saved-tag";
      btnSaveStaging.disabled = true;
      btnSaveStaging.textContent = "✅ Guardada";
      btnDiscardStaging.disabled = true;
      stagingCustomLabel.disabled = true;
      tab2Badge.textContent = "Guardada";
      tab2Badge.classList.remove("hidden");
    } else {
      stagingBanner.classList.remove("saved-mode");
      stagingBadgePill.textContent = "Área Temporal";
      stagingBadgePill.className = "staging-badge";
      stagingSaveStatus.textContent = "(No guardada)";
      stagingSaveStatus.className = "staging-unsaved";
      btnSaveStaging.disabled = false;
      btnSaveStaging.textContent = "💾 Guardar Simulación";
      btnDiscardStaging.disabled = false;
      stagingCustomLabel.disabled = false;
      tab2Badge.textContent = "Staging";
      tab2Badge.classList.remove("hidden");
    }

    // 1. Fetch Summary (KPIs)
    try {
      const sumRes = await fetch(`/api/results/summary?source=${source}&folder=${folder}&iteration=${activeIteration}`);
      if (sumRes.ok) {
        const summary = await sumRes.json();
        renderSummaryKPIs(summary);
        updateIterationDropdown(summary.num_iterations || 1);
      }
    } catch (err) {
      console.error("Error cargando summary:", err);
    }

    // 2. Fetch Chronogram
    try {
      const chronoRes = await fetch(`/api/results/chronogram?source=${source}&folder=${folder}&iteration=${activeIteration}`);
      if (chronoRes.ok) {
        const chronoData = await chronoRes.json();
        lastChronoData = chronoData;
        if (chronoCanvas) {
          chronoCanvas.loadData(chronoData);
        }
        if (hybridSyncController) {
          hybridSyncController.loadData(chronoData);
        }
      }
    } catch (err) {
      console.error("Error cargando chronogram:", err);
    }

    // 3. Fetch Packets
    loadPacketsData(source, folder, 0, packetsLimit);

    // 4. Update Hybrid View if active
    if (activeSubview === "hybrid") {
      initHybridController();
      if (hybridSyncController && lastChronoData) {
        hybridSyncController.loadData(lastChronoData);
        hybridSyncController.render();
      }
    }
  }

  function updatePresetLabels() {
    presetButtons.forEach(btn => {
      const p = btn.getAttribute("data-preset");
      if (p === "all") {
        btn.textContent = "Total";
      } else {
        btn.textContent = currentSimUnit === "cycles" ? `${p}k c` : `${p} µs`;
      }
    });

    hybridPresetButtons.forEach(btn => {
      const p = btn.getAttribute("data-preset");
      if (p === "all") {
        btn.textContent = "Total";
      } else {
        btn.textContent = currentSimUnit === "cycles" ? `${p}k c` : `${p} µs`;
      }
    });
  }

  function setSimUnit(unit) {
    currentSimUnit = unit;
    window.activeSimUnit = unit;
    if (btnUnitCycles && btnUnitTime) {
      if (unit === "cycles") {
        btnUnitCycles.classList.add("active");
        btnUnitTime.classList.remove("active");
      } else {
        btnUnitTime.classList.add("active");
        btnUnitCycles.classList.remove("active");
      }
    }
    updatePresetLabels();
    if (lastSummaryData) {
      renderSummaryKPIs(lastSummaryData);
    }
    if (chronoCanvas) {
      if (chronoCanvas.data) {
        const span = chronoCanvas.viewEndNs - chronoCanvas.viewStartNs;
        if (chronoWindowInfo) {
          chronoWindowInfo.textContent = `Ventana: ${formatSimUnit(chronoCanvas.viewStartNs)} ➔ ${formatSimUnit(chronoCanvas.viewEndNs)} (${formatSimUnit(span, true)})`;
        }
        if (chronoScrubberPos) {
          chronoScrubberPos.textContent = formatSimUnit(chronoCanvas.viewStartNs);
        }
      }
      chronoCanvas.render();
    }
    if (packetFlightCanvas) {
      packetFlightCanvas.render();
    }
    if (hybridSyncController) {
      const span = hybridSyncController.viewEndNs - hybridSyncController.viewStartNs;
      if (hybridWindowInfo) {
        hybridWindowInfo.textContent = `Ventana: ${formatSimUnit(hybridSyncController.viewStartNs)} ➔ ${formatSimUnit(hybridSyncController.viewEndNs)} (${formatSimUnit(span, true)})`;
      }
      if (hybridScrubberPos) {
        hybridScrubberPos.textContent = formatSimUnit(hybridSyncController.viewStartNs);
      }
      hybridSyncController.render();
    }
  }

  if (btnUnitCycles) {
    btnUnitCycles.addEventListener("click", () => setSimUnit("cycles"));
  }
  if (btnUnitTime) {
    btnUnitTime.addEventListener("click", () => setSimUnit("time"));
  }

  function renderSummaryKPIs(s) {
    lastSummaryData = s;
    if (currentSimUnit === "cycles") {
      const wcVal = s.wall_clock_ns != null ? s.wall_clock_ns : (s.wall_clock_us * 1000);
      kpiWallclock.textContent = `${Math.round(wcVal).toLocaleString()} c`;
      kpiCompute.textContent = `${Math.round(s.compute_ns != null ? s.compute_ns : s.compute_time_ns).toLocaleString()} c`;
      kpiTransit.textContent = `${Math.round(s.transit_ns != null ? s.transit_ns : s.network_time_ns).toLocaleString()} c`;
      kpiStalls.textContent = `${Math.round(s.stall_ns != null ? s.stall_ns : s.stall_time_ns).toLocaleString()} c`;
    } else {
      kpiWallclock.textContent = `${s.wall_clock_us.toFixed(2)} µs`;
      kpiCompute.textContent = formatTimeNs(s.compute_time_ns);
      kpiTransit.textContent = formatTimeNs(s.network_time_ns);
      kpiStalls.textContent = formatTimeNs(s.stall_time_ns);
    }

    kpiComputeSub.textContent = `${s.compute_pct.toFixed(1)}% del tiempo total`;
    kpiTransitSub.textContent = `${s.network_pct.toFixed(1)}% del tiempo total`;
    kpiStallsSub.textContent = `${s.stall_pct.toFixed(1)}% del tiempo total`;

    kpiLambda.textContent = `${s.real_injection_rate_lambda.toFixed(4)} f/c/nodo`;
    kpiFlitLat.textContent = `${s.avg_flit_lat_cycles.toFixed(2)} ciclos`;

    kpiTotalPkts.textContent = `${s.total_packets.toLocaleString()} pkts`;
    kpiTotalFlitsSub.textContent = `${s.total_flits.toLocaleString()} flits transmitidos`;
  }

  async function loadPacketsData(source, folder, offset, limit, regime = null) {
    let url = `/api/results/packets?source=${source}&folder=${folder}&offset=${offset}&limit=${limit}&iteration=${activeIteration}`;
    if (regime) {
      url += `&regime=${regime}`;
    }

    try {
      const res = await fetch(url);
      if (res.ok) {
        const pData = await res.json();
        packetsOffset = pData.offset || 0;
        packetsTotalCount = pData.total_packets || 0;

        if (packetFlightCanvas) {
          packetFlightCanvas.loadData(pData);
        }

        const count = pData.packets ? pData.packets.length : 0;
        const endIdx = packetsOffset + count;
        packetsPageInfo.textContent = `Mostrando paquetes ${packetsOffset + 1} a ${endIdx} de ${packetsTotalCount.toLocaleString()}`;
        packetsScrubberPos.textContent = `Offset #${packetsOffset}`;

        if (packetsTotalCount > limit) {
          const ratio = packetsOffset / (packetsTotalCount - limit);
          packetsScrubber.value = Math.round(ratio * 1000);
        } else {
          packetsScrubber.value = 0;
        }
      }
    } catch (err) {
      console.error("Error cargando packets:", err);
    }
  }

  // Iteration Selector Change
  if (iterationSelector) {
    iterationSelector.addEventListener("change", () => {
      activeIteration = iterationSelector.value;
      loadResultsData(currentResultsSource, currentStagingFolder);
    });
  }

  // Subview Switching
  btnSubviewChrono.addEventListener("click", () => {
    activeSubview = "chrono";
    btnSubviewChrono.classList.add("active");
    btnSubviewPackets.classList.remove("active");
    btnSubviewHybrid.classList.remove("active");
    subviewChronoContainer.classList.remove("hidden");
    subviewPacketsContainer.classList.add("hidden");
    subviewHybridContainer.classList.add("hidden");
    if (chronoCanvas) chronoCanvas.render();
  });

  btnSubviewPackets.addEventListener("click", () => {
    activeSubview = "packets";
    btnSubviewPackets.classList.add("active");
    btnSubviewChrono.classList.remove("active");
    btnSubviewHybrid.classList.remove("active");
    subviewPacketsContainer.classList.remove("hidden");
    subviewChronoContainer.classList.add("hidden");
    subviewHybridContainer.classList.add("hidden");
    if (packetFlightCanvas) packetFlightCanvas.render();
  });

  btnSubviewHybrid.addEventListener("click", () => {
    activeSubview = "hybrid";
    btnSubviewHybrid.classList.add("active");
    btnSubviewChrono.classList.remove("active");
    btnSubviewPackets.classList.remove("active");
    subviewHybridContainer.classList.remove("hidden");
    subviewChronoContainer.classList.add("hidden");
    subviewPacketsContainer.classList.add("hidden");

    initHybridController();
    if (hybridSyncController) {
      if (lastChronoData) {
        hybridSyncController.loadData(lastChronoData);
      }
      hybridSyncController.render();
    }
  });

  // Chronogram Preset Buttons
  presetButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      presetButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const preset = btn.getAttribute("data-preset");
      if (chronoCanvas) {
        if (preset === "all") {
          chronoCanvas.setWindowPreset("all");
        } else {
          chronoCanvas.setWindowPreset(parseFloat(preset));
        }
      }
    });
  });

  // Chronogram Zoom Buttons
  btnChronoZoomIn.addEventListener("click", () => {
    if (chronoCanvas) chronoCanvas.zoom(0.8);
  });
  btnChronoZoomOut.addEventListener("click", () => {
    if (chronoCanvas) chronoCanvas.zoom(1.25);
  });
  btnChronoZoomReset.addEventListener("click", () => {
    if (chronoCanvas) chronoCanvas.setWindowPreset(20);
  });

  // Chronogram Scrubber Slider
  chronogramScrubber.addEventListener("input", () => {
    if (chronoCanvas) {
      const ratio = chronogramScrubber.value / 1000;
      chronoCanvas.setScrubberRatio(ratio);
    }
  });

  // Hybrid Preset Buttons
  hybridPresetButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      hybridPresetButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const preset = btn.getAttribute("data-preset");
      if (hybridSyncController) {
        if (preset === "all") {
          hybridSyncController.setWindowPreset("all");
        } else {
          hybridSyncController.setWindowPreset(parseFloat(preset));
        }
      }
    });
  });

  // Hybrid Zoom Buttons
  if (btnHybridZoomIn) {
    btnHybridZoomIn.addEventListener("click", () => {
      if (hybridSyncController) hybridSyncController.zoom(0.8);
    });
  }
  if (btnHybridZoomOut) {
    btnHybridZoomOut.addEventListener("click", () => {
      if (hybridSyncController) hybridSyncController.zoom(1.25);
    });
  }
  if (btnHybridZoomReset) {
    btnHybridZoomReset.addEventListener("click", () => {
      if (hybridSyncController) hybridSyncController.setWindowPreset(20);
    });
  }

  // Hybrid Scrubber Slider
  if (hybridScrubber) {
    hybridScrubber.addEventListener("input", () => {
      if (hybridSyncController) {
        const ratio = hybridScrubber.value / 1000;
        hybridSyncController.setScrubberRatio(ratio);
      }
    });
  }

  // Packet Regime Jump Buttons
  btnRegimeFree.addEventListener("click", () => {
    loadPacketsData(currentResultsSource, currentStagingFolder, 0, packetsLimit, "free");
  });
  btnRegimeMedium.addEventListener("click", () => {
    loadPacketsData(currentResultsSource, currentStagingFolder, 0, packetsLimit, "medium");
  });
  btnRegimeCritical.addEventListener("click", () => {
    loadPacketsData(currentResultsSource, currentStagingFolder, 0, packetsLimit, "critical");
  });

  // Packets Limit Selector
  packetsLimitSelect.addEventListener("change", () => {
    packetsLimit = parseInt(packetsLimitSelect.value, 10) || 100;
    loadPacketsData(currentResultsSource, currentStagingFolder, packetsOffset, packetsLimit);
  });

  // Packets Scrubber Slider
  packetsScrubber.addEventListener("input", () => {
    if (packetsTotalCount > packetsLimit) {
      const ratio = packetsScrubber.value / 1000;
      const targetOffset = Math.round(ratio * (packetsTotalCount - packetsLimit));
      loadPacketsData(currentResultsSource, currentStagingFolder, targetOffset, packetsLimit);
    }
  });

  // Save Simulation Button
  btnSaveStaging.addEventListener("click", async () => {
    if (!currentStagingFolder || currentResultsSource === "saved") return;

    const label = stagingCustomLabel.value.trim();
    btnSaveStaging.disabled = true;
    btnSaveStaging.textContent = "Guardando...";

    try {
      const res = await fetch("/api/results/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folder_name: currentStagingFolder,
          label: label
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }

      // Successfully saved!
      currentResultsSource = "saved";
      currentStagingFolder = data.saved_folder_name;

      stagingBanner.classList.add("saved-mode");
      stagingBadgePill.textContent = "Guardada en Historial";
      stagingBadgePill.className = "staging-badge saved";
      stagingFolderName.textContent = currentStagingFolder;
      stagingSaveStatus.textContent = "(Guardada)";
      stagingSaveStatus.className = "staging-saved-tag";

      btnSaveStaging.textContent = "✅ Guardada";
      btnSaveStaging.disabled = true;
      btnDiscardStaging.disabled = true;
      stagingCustomLabel.disabled = true;

      tab2Badge.textContent = "Guardada";
      alert(`¡Simulación guardada con éxito en el historial!\nRuta: build/results/${currentStagingFolder}`);

    } catch (err) {
      alert(`Error al guardar la simulación:\n${err.message}`);
      btnSaveStaging.disabled = false;
      btnSaveStaging.textContent = "💾 Guardar Simulación";
    }
  });

  // Discard Simulation Button
  btnDiscardStaging.addEventListener("click", async () => {
    if (!currentStagingFolder || currentResultsSource === "saved") return;

    const confirmDiscard = confirm(
      `¿Estás seguro de que deseas descartar y eliminar la simulación temporal "${currentStagingFolder}"?\nEsta acción no se puede deshacer.`
    );
    if (!confirmDiscard) return;

    btnDiscardStaging.disabled = true;
    btnDiscardStaging.textContent = "Descartando...";

    try {
      const res = await fetch("/api/results/discard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_name: currentStagingFolder })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }

      // Reset state and switch to tab 1
      currentStagingFolder = null;
      stagingFolderName.textContent = "Ninguna simulación activa";
      stagingSaveStatus.textContent = "(No guardada)";
      btnSaveStaging.disabled = true;
      btnDiscardStaging.disabled = true;
      btnDiscardStaging.textContent = "🗑️ Descartar";
      stagingCustomLabel.value = "";
      tab2Badge.classList.add("hidden");

      if (chronoCanvas) chronoCanvas.loadData({ num_gpus: 0, tracks: [] });
      if (packetFlightCanvas) packetFlightCanvas.loadData({ packets: [] });
      if (hybridSyncController) hybridSyncController.loadData({ num_gpus: 0, tracks: [] });
      lastChronoData = null;
      activeIteration = "last";
      if (iterationSelector) {
        iterationSelector.innerHTML = '<option value="last" selected>Última Iteración (Steady-State)</option>';
      }

      alert("Simulación temporal descartada correctamente.");
      switchTab("tab-config");

    } catch (err) {
      alert(`Error al descartar simulación:\n${err.message}`);
      btnDiscardStaging.disabled = false;
      btnDiscardStaging.textContent = "🗑️ Descartar";
    }
  });

  // =========================================================================
  // Tab 3: History & Comparative Analysis Controller (Fase 3)
  // =========================================================================
  const historyFilterModel = document.getElementById("history-filter-model");
  const historyFilterTopo = document.getElementById("history-filter-topo");
  const historySearchInput = document.getElementById("history-search-input");
  const btnRefreshHistory = document.getElementById("btn-refresh-history");

  const chkSelectAllHistory = document.getElementById("chk-select-all-history");
  const historySelectedCount = document.getElementById("history-selected-count");
  const btnSelectAllHistory = document.getElementById("btn-select-all-history");
  const btnDeselectAllHistory = document.getElementById("btn-deselect-all-history");
  const historyTableBody = document.getElementById("history-table-body");

  const btnRunComparison = document.getElementById("btn-run-comparison");
  const btnRunComparisonText = document.getElementById("btn-run-comparison-text");
  const chkSemilogSaturation = document.getElementById("chk-semilog-saturation");
  const btnExportCsv = document.getElementById("btn-export-csv");
  const comparisonStatusTag = document.getElementById("comparison-status-tag");
  const comparisonPlaceholder = document.getElementById("comparison-placeholder");
  const comparisonContent = document.getElementById("comparison-content");
  const comparisonMetricsBody = document.getElementById("comparison-metrics-body");

  const chartImgAnatomia = document.getElementById("chart-img-anatomia");
  const chartImgPrimitivas = document.getElementById("chart-img-primitivas");
  const chartImgSaturacion = document.getElementById("chart-img-saturacion");
  const saturacionEmptyNotice = document.getElementById("saturacion-empty-notice");
  const btnDownloadButtons = document.querySelectorAll(".btn-download-chart");

  let historySimulations = [];
  let selectedSimulations = new Set();
  let comparisonData = null;

  async function loadHistoryList() {
    try {
      if (historyTableBody) {
        historyTableBody.innerHTML = `<tr><td colspan="7" class="table-empty-row">Consultando catálogo en build/results/...</td></tr>`;
      }
      const res = await fetch("/api/history/list");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      historySimulations = data.simulations || [];
      renderHistoryTable();
    } catch (err) {
      console.error("Error cargando historial:", err);
      if (historyTableBody) {
        historyTableBody.innerHTML = `<tr><td colspan="7" class="table-empty-row" style="color:#ef4444;">❌ Error cargando catálogo: ${err.message}</td></tr>`;
      }
    }
  }

  function renderHistoryTable() {
    if (!historyTableBody) return;

    const filterModel = historyFilterModel ? historyFilterModel.value : "all";
    const filterTopo = historyFilterTopo ? historyFilterTopo.value : "all";
    const searchQuery = historySearchInput ? historySearchInput.value.trim().toLowerCase() : "";

    const filtered = historySimulations.filter(sim => {
      if (filterModel !== "all" && sim.model.toLowerCase() !== filterModel.toLowerCase()) {
        return false;
      }
      if (filterTopo !== "all" && sim.topology.toLowerCase() !== filterTopo.toLowerCase()) {
        return false;
      }
      if (searchQuery) {
        const textTarget = `${sim.folder} ${sim.label || ""} ${sim.model} ${sim.topology} bs${sim.batch_size}`.toLowerCase();
        if (!textTarget.includes(searchQuery)) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      historyTableBody.innerHTML = `<tr><td colspan="7" class="table-empty-row">No se encontraron simulaciones que coincidan con los filtros.</td></tr>`;
      updateSelectionSummary(filtered);
      return;
    }

    let html = "";
    filtered.forEach(sim => {
      const isChecked = selectedSimulations.has(sim.folder) ? "checked" : "";
      const isStaging = sim.source === "staging";
      const rowClass = isStaging ? "row-staging" : "";

      const labelBadge = sim.label ? `<span class="folder-label-tag">🏷️ ${escapeHtml(sim.label)}</span>` : "";
      const stagingBadge = isStaging ? `<span class="badge-staging">TEMPORAL (No guardada)</span>` : "";

      const modelBadge = sim.model === "deepseekV3" ? "badge-scatter" : (sim.model === "mixtral" ? "badge-calc" : "badge-allreduce");
      const modelName = sim.model === "deepseekV3" ? "DeepSeek-V3" : (sim.model === "mixtral" ? "Mixtral 8x7B" : sim.model.toUpperCase());

      const tpTag = sim.tensor_degree > 1 ? `<span class="param-pill">TP=${sim.tensor_degree}</span>` : "";
      const skewTag = sim.skewness > 0 ? `<span class="param-pill">Skew=${sim.skewness}</span>` : "";
      const vcsTag = `<span class="param-pill">VCs=${sim.vcs}</span>`;
      const bsTag = `<span class="param-pill">BS=${sim.batch_size}</span>`;

      html += `
        <tr class="${rowClass}" data-folder="${escapeHtml(sim.folder)}">
          <td class="td-chk">
            <input type="checkbox" class="chk-history-item" data-folder="${escapeHtml(sim.folder)}" ${isChecked}>
          </td>
          <td class="td-folder">
            <div class="folder-cell">
              <div class="folder-title-row">
                <span class="folder-name-text">${escapeHtml(sim.folder)}</span>
                ${stagingBadge}
                ${labelBadge}
              </div>
            </div>
          </td>
          <td class="td-model">
            <span class="badge ${modelBadge}">${modelName}</span>
          </td>
          <td class="td-topo">
            <strong>${escapeHtml(sim.topology.toUpperCase())}</strong>
            <span style="color:var(--text-dim);font-size:0.74rem;">(${sim.num_gpus} GPUs)</span>
          </td>
          <td class="td-params">
            <div class="params-pill-group">
              ${bsTag}
              ${vcsTag}
              ${tpTag}
              ${skewTag}
            </div>
          </td>
          <td class="td-date" style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted);">
            ${escapeHtml(sim.saved_at || "N/A")}
          </td>
          <td class="td-actions">
            <div class="actions-cell">
              <button class="btn-action-icon btn-open-viewer" data-folder="${escapeHtml(sim.folder)}" data-source="${sim.source}" title="Cargar en Pestaña 2 y abrir visores interactivos">
                👁️ Abrir en Visor
              </button>
              <button class="btn-action-icon btn-edit-label" data-folder="${escapeHtml(sim.folder)}" data-label="${escapeHtml(sim.label || '')}" title="Editar etiqueta descriptiva" ${isStaging ? 'disabled' : ''}>
                🏷️
              </button>
              <button class="btn-action-icon btn-action-delete" data-folder="${escapeHtml(sim.folder)}" title="Eliminar simulación del historial" ${isStaging ? 'disabled' : ''}>
                🗑️
              </button>
            </div>
          </td>
        </tr>
      `;
    });

    historyTableBody.innerHTML = html;
    updateSelectionSummary(filtered);
    bindHistoryRowEvents();
  }

  function updateSelectionSummary(visibleSims) {
    if (!historySelectedCount) return;
    const totalCount = selectedSimulations.size;
    historySelectedCount.textContent = `${totalCount} simulaciones seleccionadas`;

    if (btnRunComparison && btnRunComparisonText) {
      if (totalCount > 0) {
        btnRunComparison.disabled = false;
        btnRunComparisonText.textContent = `Generar Comparativa (${totalCount} seleccionadas)`;
      } else {
        btnRunComparison.disabled = true;
        btnRunComparisonText.textContent = `Generar Comparativa (0 seleccionadas)`;
      }
    }

    if (chkSelectAllHistory && visibleSims) {
      const allVisibleSelected = visibleSims.length > 0 && visibleSims.every(s => selectedSimulations.has(s.folder));
      chkSelectAllHistory.checked = allVisibleSelected;
    }
  }

  function bindHistoryRowEvents() {
    if (!historyTableBody) return;

    // Checkbox clicks
    const checkboxes = historyTableBody.querySelectorAll(".chk-history-item");
    checkboxes.forEach(chk => {
      chk.addEventListener("change", (e) => {
        const folder = e.target.getAttribute("data-folder");
        if (e.target.checked) {
          selectedSimulations.add(folder);
        } else {
          selectedSimulations.delete(folder);
        }
        updateSelectionSummary(historySimulations);
      });
    });

    // Abrir en Visor (Pestaña 2)
    const openBtns = historyTableBody.querySelectorAll(".btn-open-viewer");
    openBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const folder = btn.getAttribute("data-folder");
        const source = btn.getAttribute("data-source") || "saved";
        switchTab("tab-results");
        loadResultsData(source, folder);
      });
    });

    // Etiquetar
    const labelBtns = historyTableBody.querySelectorAll(".btn-edit-label");
    labelBtns.forEach(btn => {
      btn.addEventListener("click", async () => {
        const folder = btn.getAttribute("data-folder");
        const currentLabel = btn.getAttribute("data-label") || "";
        const newLabel = prompt(`Introduce una etiqueta descriptiva para la simulación "${folder}":`, currentLabel);
        if (newLabel === null) return;

        try {
          const res = await fetch("/api/history/label", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder: folder, label: newLabel.trim() })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
          loadHistoryList();
        } catch (err) {
          alert(`Error al guardar etiqueta:\n${err.message}`);
        }
      });
    });

    // Eliminar
    const delBtns = historyTableBody.querySelectorAll(".btn-action-delete");
    delBtns.forEach(btn => {
      btn.addEventListener("click", async () => {
        const folder = btn.getAttribute("data-folder");
        const ok = confirm(`¿Estás seguro de que deseas eliminar permanentemente la simulación "${folder}" de build/results/?\nEsta acción no se puede deshacer.`);
        if (!ok) return;

        try {
          const res = await fetch("/api/history/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder: folder })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
          selectedSimulations.delete(folder);
          loadHistoryList();
        } catch (err) {
          alert(`Error al eliminar simulación:\n${err.message}`);
        }
      });
    });
  }

  // Filter events
  if (historyFilterModel) historyFilterModel.addEventListener("change", renderHistoryTable);
  if (historyFilterTopo) historyFilterTopo.addEventListener("change", renderHistoryTable);
  if (historySearchInput) historySearchInput.addEventListener("input", renderHistoryTable);
  if (btnRefreshHistory) btnRefreshHistory.addEventListener("click", loadHistoryList);

  // Selection tools
  if (chkSelectAllHistory) {
    chkSelectAllHistory.addEventListener("change", () => {
      const isChecked = chkSelectAllHistory.checked;
      const checkboxes = historyTableBody.querySelectorAll(".chk-history-item");
      checkboxes.forEach(chk => {
        chk.checked = isChecked;
        const folder = chk.getAttribute("data-folder");
        if (isChecked) selectedSimulations.add(folder);
        else selectedSimulations.delete(folder);
      });
      updateSelectionSummary(historySimulations);
    });
  }

  if (btnSelectAllHistory) {
    btnSelectAllHistory.addEventListener("click", () => {
      const checkboxes = historyTableBody.querySelectorAll(".chk-history-item");
      checkboxes.forEach(chk => {
        chk.checked = true;
        selectedSimulations.add(chk.getAttribute("data-folder"));
      });
      updateSelectionSummary(historySimulations);
    });
  }

  if (btnDeselectAllHistory) {
    btnDeselectAllHistory.addEventListener("click", () => {
      selectedSimulations.clear();
      const checkboxes = historyTableBody.querySelectorAll(".chk-history-item");
      checkboxes.forEach(chk => { chk.checked = false; });
      updateSelectionSummary(historySimulations);
    });
  }

  // Comparison Runner
  if (btnRunComparison) {
    btnRunComparison.addEventListener("click", runComparison);
  }

  if (chkSemilogSaturation) {
    chkSemilogSaturation.addEventListener("change", () => {
      if (selectedSimulations.size > 0 && comparisonContent && !comparisonContent.classList.contains("hidden")) {
        runComparison();
      }
    });
  }

  async function runComparison() {
    if (selectedSimulations.size === 0) return;

    btnRunComparison.disabled = true;
    if (comparisonStatusTag) {
      comparisonStatusTag.classList.remove("hidden");
      comparisonStatusTag.textContent = "Calculando métricas y generando figuras en memoria...";
    }

    const simSpecs = [];
    selectedSimulations.forEach(folder => {
      const item = historySimulations.find(s => s.folder === folder);
      simSpecs.push({
        source: item ? item.source : "saved",
        folder: folder
      });
    });

    try {
      const res = await fetch("/api/analysis/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          simulations: simSpecs,
          semilog: chkSemilogSaturation ? chkSemilogSaturation.checked : false
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

      comparisonData = data;
      renderComparisonResults(data);
    } catch (err) {
      alert(`Error al generar comparativa:\n${err.message}`);
    } finally {
      btnRunComparison.disabled = false;
      if (comparisonStatusTag) comparisonStatusTag.classList.add("hidden");
    }
  }

  function renderComparisonResults(data) {
    if (comparisonPlaceholder) comparisonPlaceholder.classList.add("hidden");
    if (comparisonContent) comparisonContent.classList.remove("hidden");
    if (btnExportCsv) btnExportCsv.disabled = false;

    // Render Metrics Table
    const rows = data.rows || [];
    let tableHtml = "";
    rows.forEach(r => {
      const isStaging = r.is_unsaved;
      const tag = isStaging ? `<span class="badge-staging">TEMPORAL</span> ` : "";
      tableHtml += `
        <tr>
          <td><strong>${tag}${escapeHtml(r.label || r.folder)}</strong></td>
          <td><span class="badge ${r.model === 'deepseekV3' ? 'badge-scatter' : 'badge-calc'}">${escapeHtml(r.model)}</span></td>
          <td>${escapeHtml(r.topology.toUpperCase())}</td>
          <td>${r.num_gpus}</td>
          <td style="color:#38bdf8;font-weight:700;">${r.wall_clock_us.toFixed(2)} µs</td>
          <td>${r.compute_us.toFixed(2)} µs <span style="color:var(--text-dim);">(${r.compute_pct.toFixed(1)}%)</span></td>
          <td>${r.transit_us.toFixed(2)} µs <span style="color:var(--text-dim);">(${r.transit_pct.toFixed(1)}%)</span></td>
          <td style="color:#ef4444;">${r.stall_us.toFixed(2)} µs <span style="color:var(--text-dim);">(${r.stall_pct.toFixed(1)}%)</span></td>
          <td>${r.scatter_us.toFixed(2)} µs</td>
          <td>${r.gather_us.toFixed(2)} µs</td>
          <td>${r.allreduce_us > 0 ? r.allreduce_us.toFixed(2) + ' µs' : '--'}</td>
          <td style="color:#10b981;font-weight:600;">${r.lambda_flits.toFixed(4)}</td>
          <td>${r.avg_flit_lat_cycles > 0 ? r.avg_flit_lat_cycles.toFixed(1) + ' c' : '--'}</td>
          <td>${r.avg_pkt_lat_cycles > 0 ? r.avg_pkt_lat_cycles.toFixed(1) + ' c' : '--'}</td>
          <td>${r.total_packets.toLocaleString()}</td>
        </tr>
      `;
    });
    if (comparisonMetricsBody) {
      comparisonMetricsBody.innerHTML = tableHtml;
    }

    // Render Charts
    const charts = data.charts || {};
    if (chartImgAnatomia && charts.anatomia_latencia) {
      chartImgAnatomia.src = charts.anatomia_latencia;
    }
    if (chartImgPrimitivas && charts.desglose_primitivas_moe) {
      chartImgPrimitivas.src = charts.desglose_primitivas_moe;
    }
    if (chartImgSaturacion) {
      if (charts.curva_saturacion_red) {
        chartImgSaturacion.src = charts.curva_saturacion_red;
        chartImgSaturacion.classList.remove("hidden");
        if (saturacionEmptyNotice) saturacionEmptyNotice.classList.add("hidden");
      } else {
        chartImgSaturacion.src = "";
        chartImgSaturacion.classList.add("hidden");
        if (saturacionEmptyNotice) saturacionEmptyNotice.classList.remove("hidden");
      }
    }
  }

  // Export CSV
  if (btnExportCsv) {
    btnExportCsv.addEventListener("click", () => {
      if (!comparisonData || !comparisonData.rows || comparisonData.rows.length === 0) return;
      const rows = comparisonData.rows;

      const headers = [
        "Configuración", "Etiqueta", "Modelo", "Topología", "Num_GPUs", "VCs", "Batch_Size", "TP", "Skewness",
        "Wall_Clock_us", "Compute_us", "Compute_pct", "Transit_us", "Transit_pct", "Stall_us", "Stall_pct",
        "Scatter_us", "Gather_us", "AllReduce_us", "Lambda_flits_cyc_node", "Avg_Flit_Lat_cycles", "Avg_Pkt_Lat_cycles", "Total_Packets"
      ];

      const csvLines = [headers.join(",")];
      rows.forEach(r => {
        const line = [
          `"${r.folder}"`,
          `"${(r.label || r.folder).replace(/"/g, '""')}"`,
          `"${r.model}"`,
          `"${r.topology}"`,
          r.num_gpus,
          r.vcs,
          r.batch_size,
          r.tp,
          r.skewness,
          r.wall_clock_us,
          r.compute_us,
          r.compute_pct,
          r.transit_us,
          r.transit_pct,
          r.stall_us,
          r.stall_pct,
          r.scatter_us,
          r.gather_us,
          r.allreduce_us,
          r.lambda_flits,
          r.avg_flit_lat_cycles,
          r.avg_pkt_lat_cycles,
          r.total_packets
        ];
        csvLines.push(line.join(","));
      });

      const csvContent = csvLines.join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `comparativa_simulaciones_tfm_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    });
  }

  // Download Charts Individual PNG
  btnDownloadButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const chartKey = btn.getAttribute("data-chart");
      let src = "";
      if (chartKey === "anatomia" && chartImgAnatomia) src = chartImgAnatomia.src;
      else if (chartKey === "primitivas" && chartImgPrimitivas) src = chartImgPrimitivas.src;
      else if (chartKey === "saturacion" && chartImgSaturacion) src = chartImgSaturacion.src;

      if (!src || !src.startsWith("data:image/png")) {
        alert("La gráfica aún no está disponible para descargar.");
        return;
      }

      const link = document.createElement("a");
      link.href = src;
      link.download = `figura_${chartKey}_tfm_${new Date().toISOString().slice(0, 10)}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
  });

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // =========================================================================
  // Initialization
  // =========================================================================
  initCanvases();
  updatePresetLabels();
  updateDynamicControls();
  loadHistoryList();

  // Initial check on page load to see if staging exists
  fetch("/api/results/active")
    .then(r => r.json())
    .then(data => {
      if (data.active && data.folder_name) {
        currentStagingFolder = data.folder_name;
        currentResultsSource = data.source || "staging";
        loadResultsData(currentResultsSource, currentStagingFolder);
      }
    })
    .catch(() => {});

  fetch("/api/status")
    .then(r => r.json())
    .then(data => {
      if (data.status === "running") {
        isSimulating = true;
        btnRunSim.disabled = true;
        btnAbortSim.disabled = false;
        updateLiveStatus("running");
        startTimer();
        startPolling();
      }
    })
    .catch(() => {});
});

