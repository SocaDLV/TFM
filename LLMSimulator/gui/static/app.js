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
  const stagingFolderName = document.getElementById("staging-folder-name");
  const stagingSaveStatus = document.getElementById("staging-save-status");
  const btnSaveStaging = document.getElementById("btn-save-staging");
  const btnDiscardStaging = document.getElementById("btn-discard-staging");

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

          // Update staging banner in Tab 2
          stagingFolderName.textContent = currentStagingFolder || "Carpeta temporal lista";
          stagingSaveStatus.textContent = "(No guardada)";
          btnSaveStaging.disabled = false;
          btnDiscardStaging.disabled = false;
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

  // Initial setup call
  updateDynamicControls();

  // Initial check on page load to see if staging exists
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
      } else if (data.status === "completed" && data.staging_folder_name) {
        currentStagingFolder = data.staging_folder_name;
        tab2Badge.classList.remove("hidden");
        stagingFolderName.textContent = currentStagingFolder;
        stagingSaveStatus.textContent = "(No guardada)";
        btnSaveStaging.disabled = false;
        btnDiscardStaging.disabled = false;
      }
    })
    .catch(() => {});
});

