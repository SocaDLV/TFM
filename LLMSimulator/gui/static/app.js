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
  const subviewChronoContainer = document.getElementById("subview-chrono-container");
  const subviewPacketsContainer = document.getElementById("subview-packets-container");

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

  // Tab 2 Canvas Controllers
  let chronoCanvas = null;
  let packetFlightCanvas = null;
  let currentResultsSource = "staging";
  let packetsOffset = 0;
  let packetsLimit = 100;
  let packetsTotalCount = 0;

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
        }
      }, 50);
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
          const spanUs = (endNs - startNs) / 1000;
          chronoWindowInfo.textContent = `Ventana: ${(startNs / 1000).toFixed(2)} µs ➔ ${(endNs / 1000).toFixed(2)} µs (${spanUs.toFixed(2)} µs)`;
          chronoScrubberPos.textContent = `${(startNs / 1000).toFixed(2)} µs`;

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
      const sumRes = await fetch(`/api/results/summary?source=${source}&folder=${folder}`);
      if (sumRes.ok) {
        const summary = await sumRes.json();
        renderSummaryKPIs(summary);
      }
    } catch (err) {
      console.error("Error cargando summary:", err);
    }

    // 2. Fetch Chronogram
    try {
      const chronoRes = await fetch(`/api/results/chronogram?source=${source}&folder=${folder}`);
      if (chronoRes.ok) {
        const chronoData = await chronoRes.json();
        if (chronoCanvas) {
          chronoCanvas.loadData(chronoData);
        }
      }
    } catch (err) {
      console.error("Error cargando chronogram:", err);
    }

    // 3. Fetch Packets
    loadPacketsData(source, folder, 0, packetsLimit);
  }

  function renderSummaryKPIs(s) {
    kpiWallclock.textContent = `${s.wall_clock_us.toFixed(2)} µs`;

    kpiCompute.textContent = formatTimeNs(s.compute_time_ns);
    kpiComputeSub.textContent = `${s.compute_pct.toFixed(1)}% del tiempo total`;

    kpiTransit.textContent = formatTimeNs(s.network_time_ns);
    kpiTransitSub.textContent = `${s.network_pct.toFixed(1)}% del tiempo total`;

    kpiStalls.textContent = formatTimeNs(s.stall_time_ns);
    kpiStallsSub.textContent = `${s.stall_pct.toFixed(1)}% del tiempo total`;

    kpiLambda.textContent = `${s.real_injection_rate_lambda.toFixed(4)} f/c/nodo`;
    kpiFlitLat.textContent = `${s.avg_flit_lat_cycles.toFixed(2)} ciclos`;

    kpiTotalPkts.textContent = `${s.total_packets.toLocaleString()} pkts`;
    kpiTotalFlitsSub.textContent = `${s.total_flits.toLocaleString()} flits transmitidos`;
  }

  async function loadPacketsData(source, folder, offset, limit, regime = null) {
    let url = `/api/results/packets?source=${source}&folder=${folder}&offset=${offset}&limit=${limit}`;
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

  // Subview Switching
  btnSubviewChrono.addEventListener("click", () => {
    btnSubviewChrono.classList.add("active");
    btnSubviewPackets.classList.remove("active");
    subviewChronoContainer.classList.remove("hidden");
    subviewPacketsContainer.classList.add("hidden");
    if (chronoCanvas) chronoCanvas.render();
  });

  btnSubviewPackets.addEventListener("click", () => {
    btnSubviewPackets.classList.add("active");
    btnSubviewChrono.classList.remove("active");
    subviewPacketsContainer.classList.remove("hidden");
    subviewChronoContainer.classList.add("hidden");
    if (packetFlightCanvas) packetFlightCanvas.render();
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

      alert("Simulación temporal descartada correctamente.");
      switchTab("tab-config");

    } catch (err) {
      alert(`Error al descartar simulación:\n${err.message}`);
      btnDiscardStaging.disabled = false;
      btnDiscardStaging.textContent = "🗑️ Descartar";
    }
  });

  // =========================================================================
  // Initialization
  // =========================================================================
  initCanvases();
  updateDynamicControls();

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

