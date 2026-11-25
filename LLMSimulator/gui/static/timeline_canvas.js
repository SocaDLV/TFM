/**
 * LLM-NoC Co-Simulation Workbench - Interactive HTML5 Canvas Renderers
 * Provides high-performance, on-the-fly rendering for:
 * 1. ChronogramCanvas: GPU cycle-by-cycle causal chronogram (tracks GPU 0..N-1)
 * 2. PacketFlightCanvas: BookSim2 in-flight packet Gantt chart (Queue + Flight)
 */

// Global simulation unit state (default: 'cycles')
window.activeSimUnit = window.activeSimUnit || "cycles";

// Dynamic Light/Dark palette for HTML5 Canvas renderers (Haoziwan CAD-inspired)
function getCanvasTheme() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  if (isDark) {
    return {
      isDark: true,
      bg: "#0d1117",
      headerBg: "#161b22",
      altRowBg: "rgba(255, 255, 255, 0.02)",
      hoverRowBg: "rgba(59, 130, 246, 0.16)",
      gridLine: "rgba(48, 54, 61, 0.45)",
      trackLine: "#21262d",
      axisLine: "#30363d",
      tickMark: "#484f58",
      textPrimary: "#e6edf3",
      textSecondary: "#8b949e",
      textMuted: "#6e7681",
      accent: "#3b82f6",
      crosshair: "rgba(59, 130, 246, 0.85)",
      crosshairBadgeBg: "#3b82f6",
      crosshairBadgeText: "#ffffff",
      iterMarker: "#f59e0b",
      iterMarkerText: "#000000",
      calcFill: "#10b981",
      calcStroke: "#059669",
      calcText: "#042f2e",
      scatterFill: "#38bdf8",
      scatterStroke: "#0284c7",
      scatterText: "#042f2e",
      gatherFill: "#2563eb",
      gatherStroke: "#1d4ed8",
      allreduceFill: "#a855f7",
      allreduceStroke: "#7e22ce",
      stallFill: "#ef4444",
      stallStroke: "#b91c1c",
      blockLightText: "#ffffff",
      subOpDash: "rgba(255, 255, 255, 0.4)",
      queueFill: "#e67e22",
      flightFill: "#0284c7",
      phaseScatter: "rgba(56, 189, 248, 0.06)",
      phaseGather: "rgba(37, 99, 235, 0.06)",
      phaseAllreduce: "rgba(168, 85, 247, 0.06)",
      previewLink: "#475569",
      previewWrap: "#9333ea",
      hoverEdgeStroke: "#f8fafc",
      nodeNeutralFill: "#1e293b",
      nodeNeutralStroke: "#3b82f6",
      nodeNeutralText: "#e2e8f0",
      nodeHoverHalo: "#ffffff",
      nodeSelectedStroke: "#60a5fa",
      flowOut: "#fbbf24",
      flowIn: "#f43f5e",
    };
  }
  return {
    isDark: false,
    bg: "#ffffff",
    headerBg: "#f8fafc",
    altRowBg: "rgba(15, 23, 42, 0.025)",
    hoverRowBg: "rgba(37, 99, 235, 0.10)",
    gridLine: "rgba(203, 213, 225, 0.65)",
    trackLine: "#e2e8f0",
    axisLine: "#cbd5e1",
    tickMark: "#94a3b8",
    textPrimary: "#0f172a",
    textSecondary: "#475569",
    textMuted: "#64748b",
    accent: "#2563eb",
    crosshair: "rgba(37, 99, 235, 0.85)",
    crosshairBadgeBg: "#2563eb",
    crosshairBadgeText: "#ffffff",
    iterMarker: "#d97706",
    iterMarkerText: "#ffffff",
    calcFill: "#10b981",
    calcStroke: "#059669",
    calcText: "#022c22",
    scatterFill: "#0ea5e9",
    scatterStroke: "#0284c7",
    scatterText: "#ffffff",
    gatherFill: "#2563eb",
    gatherStroke: "#1d4ed8",
    allreduceFill: "#9333ea",
    allreduceStroke: "#7e22ce",
    stallFill: "#dc2626",
    stallStroke: "#b91c1c",
    blockLightText: "#ffffff",
    subOpDash: "rgba(15, 23, 42, 0.25)",
    queueFill: "#d97706",
    flightFill: "#0284c7",
    phaseScatter: "rgba(14, 165, 233, 0.08)",
    phaseGather: "rgba(37, 99, 235, 0.08)",
    phaseAllreduce: "rgba(147, 51, 234, 0.08)",
    previewLink: "#64748b",
    previewWrap: "#7c3aed",
    hoverEdgeStroke: "#0f172a",
    nodeNeutralFill: "#f1f5f9",
    nodeNeutralStroke: "#2563eb",
    nodeNeutralText: "#0f172a",
    nodeHoverHalo: "#0f172a",
    nodeSelectedStroke: "#1d4ed8",
    flowOut: "#d97706",
    flowIn: "#e11d48",
  };
}
window.getCanvasTheme = getCanvasTheme;

// Helper to format nanoseconds into clean human-readable units (ns, µs, ms)
function formatTimeNs(ns) {
  if (ns === undefined || ns === null || isNaN(ns)) return "0 ns";
  if (ns >= 1e6) {
    return `${(ns / 1e6).toFixed(2)} ms`;
  } else if (ns >= 1e3) {
    return `${(ns / 1e3).toFixed(2)} µs`;
  } else {
    return `${Math.round(ns)} ns`;
  }
}

// Global helper to format time / cycle values based on activeSimUnit (1 GHz = 1 cycle per ns)
function formatSimUnit(nsValue, isDuration = false, unit = null) {
  const activeUnit = unit || window.activeSimUnit || "cycles";
  if (nsValue === undefined || nsValue === null || isNaN(nsValue)) {
    return activeUnit === "cycles" ? "0 c" : "0 ns";
  }

  const val = Number(nsValue);

  if (activeUnit === "cycles") {
    // 1 GHz clock model: 1 ns = 1 cycle
    if (isDuration) {
      if (Math.abs(val) >= 1e6) {
        return `${(val / 1e6).toFixed(2)}M c`;
      } else if (Math.abs(val) >= 1e3) {
        return `${(val / 1e3).toFixed(1)}k c`;
      } else {
        return `${Math.round(val).toLocaleString()} c`;
      }
    } else {
      return `${Math.round(val).toLocaleString()} c`;
    }
  } else {
    return formatTimeNs(val);
  }
}
window.formatSimUnit = formatSimUnit;

// Helper to setup HiDPI canvas
function setupHiDPICanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = rect.width || canvas.clientWidth || 1000;
  const height = rect.height || canvas.clientHeight || 450;
  
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  
  const ctx = canvas.getContext("2d");
  ctx.resetTransform();
  ctx.scale(dpr, dpr);
  
  return { width, height, dpr, ctx };
}

/* ==========================================================================
   1. ChronogramCanvas (Sub-vista A: Cronograma GPU Ciclo a Ciclo)
   ========================================================================== */
class ChronogramCanvas {
  constructor(canvasEl, tooltipEl, onViewportChange) {
    this.canvas = canvasEl;
    this.tooltip = tooltipEl;
    this.onViewportChange = onViewportChange;

    this.data = null; // { num_gpus, total_span_ns, min_time_ns, max_time_ns, tracks }
    this.viewStartNs = 0;
    this.viewEndNs = 20000; // default 20 us
    this.minTimeNs = 0;
    this.maxTimeNs = 20000;

    this.marginLeft = 85;
    this.marginRight = 20;
    this.headerHeight = 36;
    this.footerHeight = 10;

    // Interaction state
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartViewStart = 0;
    this.dragStartViewEnd = 0;

    this.hoveredBlock = null;
    this.hoveredGpu = -1;

    // Crosshair state (for synchronized hybrid split-screen view)
    this.crosshairX = null;
    this.crosshairNs = null;

    this.bindEvents();
  }

  setCrosshair(x, ns) {
    this.crosshairX = x;
    this.crosshairNs = ns;
    this.render();
  }

  clearCrosshair() {
    if (this.crosshairX !== null) {
      this.crosshairX = null;
      this.crosshairNs = null;
      this.render();
    }
  }

  bindEvents() {
    this.canvas.addEventListener("mousedown", (e) => this.handleMouseDown(e));
    window.addEventListener("mousemove", (e) => this.handleMouseMove(e));
    window.addEventListener("mouseup", (e) => this.handleMouseUp(e));
    this.canvas.addEventListener("wheel", (e) => this.handleWheel(e), { passive: false });
    this.canvas.addEventListener("mouseleave", () => this.handleMouseLeave());
    window.addEventListener("resize", () => this.render());
  }

  loadData(chronogramData) {
    this.data = chronogramData;
    this.minTimeNs = chronogramData.min_time_ns || 0;
    this.maxTimeNs = chronogramData.max_time_ns || 1;
    
    // Default initial window: 20 µs or full span if smaller
    this.viewStartNs = this.minTimeNs;
    const defaultSpan = Math.min(20000, this.maxTimeNs - this.minTimeNs);
    this.viewEndNs = this.viewStartNs + (defaultSpan > 0 ? defaultSpan : 20000);

    this.render();
    if (this.onViewportChange) {
      this.onViewportChange(this.viewStartNs, this.viewEndNs, this.minTimeNs, this.maxTimeNs);
    }
  }

  setWindowPreset(presetUs) {
    if (!this.data) return;
    const totalSpan = this.maxTimeNs - this.minTimeNs;
    
    if (presetUs === "all") {
      this.viewStartNs = this.minTimeNs;
      this.viewEndNs = this.maxTimeNs;
    } else {
      const windowNs = presetUs * 1000;
      const currentCenter = (this.viewStartNs + this.viewEndNs) / 2;
      let start = currentCenter - windowNs / 2;
      let end = currentCenter + windowNs / 2;

      if (start < this.minTimeNs) {
        start = this.minTimeNs;
        end = start + windowNs;
      }
      if (end > this.maxTimeNs) {
        end = this.maxTimeNs;
        start = Math.max(this.minTimeNs, end - windowNs);
      }
      this.viewStartNs = start;
      this.viewEndNs = end;
    }

    this.render();
    if (this.onViewportChange) {
      this.onViewportChange(this.viewStartNs, this.viewEndNs, this.minTimeNs, this.maxTimeNs);
    }
  }

  setScrubberRatio(ratio) {
    if (!this.data) return;
    const span = this.viewEndNs - this.viewStartNs;
    const maxStart = this.maxTimeNs - span;
    this.viewStartNs = this.minTimeNs + ratio * (maxStart - this.minTimeNs);
    this.viewEndNs = this.viewStartNs + span;

    this.render();
    if (this.onViewportChange) {
      this.onViewportChange(this.viewStartNs, this.viewEndNs, this.minTimeNs, this.maxTimeNs);
    }
  }

  zoom(factor, centerRatio = 0.5) {
    if (!this.data) return;
    const currentSpan = this.viewEndNs - this.viewStartNs;
    let newSpan = currentSpan * factor;
    
    // Bounds: minimum 100 ns, maximum total span * 1.5
    newSpan = Math.max(100, Math.min((this.maxTimeNs - this.minTimeNs) * 1.5, newSpan));
    
    const centerTime = this.viewStartNs + currentSpan * centerRatio;
    let newStart = centerTime - newSpan * centerRatio;
    let newEnd = newStart + newSpan;

    if (newStart < this.minTimeNs) {
      newStart = this.minTimeNs;
      newEnd = newStart + newSpan;
    }
    if (newEnd > this.maxTimeNs && (newEnd - newStart) <= (this.maxTimeNs - this.minTimeNs)) {
      newEnd = this.maxTimeNs;
      newStart = Math.max(this.minTimeNs, newEnd - newSpan);
    }

    this.viewStartNs = newStart;
    this.viewEndNs = newEnd;
    this.render();

    if (this.onViewportChange) {
      this.onViewportChange(this.viewStartNs, this.viewEndNs, this.minTimeNs, this.maxTimeNs);
    }
  }

  handleMouseDown(e) {
    if (!this.data) return;
    const rect = this.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < this.marginLeft) return;

    this.isDragging = true;
    this.dragStartX = e.clientX;
    this.dragStartViewStart = this.viewStartNs;
    this.dragStartViewEnd = this.viewEndNs;
    this.canvas.style.cursor = "grabbing";
  }

  handleMouseMove(e) {
    if (this.isDragging) {
      const rect = this.canvas.getBoundingClientRect();
      const plotWidth = rect.width - this.marginLeft - this.marginRight;
      if (plotWidth <= 0) return;

      const dx = e.clientX - this.dragStartX;
      const span = this.dragStartViewEnd - this.dragStartViewStart;
      const dt = -(dx / plotWidth) * span;

      let newStart = this.dragStartViewStart + dt;
      let newEnd = this.dragStartViewEnd + dt;

      if (newStart < this.minTimeNs) {
        newStart = this.minTimeNs;
        newEnd = newStart + span;
      }
      if (newEnd > this.maxTimeNs) {
        newEnd = this.maxTimeNs;
        newStart = Math.max(this.minTimeNs, newEnd - span);
      }

      this.viewStartNs = newStart;
      this.viewEndNs = newEnd;
      this.render();

      if (this.onViewportChange) {
        this.onViewportChange(this.viewStartNs, this.viewEndNs, this.minTimeNs, this.maxTimeNs);
      }
      return;
    }

    // Hover inspection
    if (!this.data) return;
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (mouseX < this.marginLeft || mouseX > rect.width - this.marginRight ||
        mouseY < this.headerHeight || mouseY > rect.height - this.footerHeight) {
      this.hideTooltip();
      return;
    }

    const found = this.getBlockAt(mouseX, mouseY);
    if (found) {
      this.showTooltip(found.block, found.gpuIdx, e.clientX, e.clientY);
    } else {
      this.hideTooltip();
    }
  }

  getBlockAt(x, y) {
    if (!this.data) return null;
    const rect = this.canvas.getBoundingClientRect();
    const plotWidth = rect.width - this.marginLeft - this.marginRight;
    const plotHeight = rect.height - this.headerHeight - this.footerHeight;
    const numGpus = this.data.num_gpus || 1;
    const trackHeight = plotHeight / numGpus;

    const gpuIdx = Math.floor((y - this.headerHeight) / trackHeight);
    if (gpuIdx < 0 || gpuIdx >= numGpus) return null;

    const span = this.viewEndNs - this.viewStartNs;
    if (span <= 0) return null;
    const mouseNs = this.viewStartNs + ((x - this.marginLeft) / plotWidth) * span;

    const trackBlocks = this.data.tracks[gpuIdx] || [];
    for (let i = 0; i < trackBlocks.length; i++) {
      const b = trackBlocks[i];
      if (mouseNs >= b.start_ns && mouseNs <= b.end_ns) {
        return { block: b, gpuIdx };
      }
      if (b.start_ns > mouseNs) break;
    }
    return null;
  }

  handleMouseUp() {
    if (this.isDragging) {
      this.isDragging = false;
      this.canvas.style.cursor = "crosshair";
    }
  }

  handleMouseLeave() {
    this.hideTooltip();
  }

  handleWheel(e) {
    if (!this.data) return;
    e.preventDefault();

    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const plotWidth = rect.width - this.marginLeft - this.marginRight;
    let ratio = 0.5;
    if (mouseX >= this.marginLeft && mouseX <= rect.width - this.marginRight) {
      ratio = (mouseX - this.marginLeft) / plotWidth;
    }

    const factor = e.deltaY > 0 ? 1.15 : 0.85;
    this.zoom(factor, ratio);
  }

  showTooltip(block, gpuIdx, clientX, clientY) {
    if (!this.tooltip) return;
    
    let badgeClass = "badge-calc";
    let typeName = "Cómputo / Atención";
    if (block.block_type === "scatter") {
      badgeClass = "badge-scatter";
      typeName = "Red: MoE Scatter";
    } else if (block.block_type === "gather") {
      badgeClass = "badge-gather";
      typeName = "Red: MoE Gather";
    } else if (block.block_type === "all_reduce") {
      badgeClass = "badge-allreduce";
      typeName = "Red: Ring-AllReduce";
    } else if (block.block_type === "stall") {
      badgeClass = "badge-stall";
      typeName = "Stall de Red (Espera Causal / Sincronización)";
    }

    let boundRow = "";
    if (block.block_type === "calc") {
      const memVal = block.mem_bound_pct ?? block.mem_pct;
      if (typeof memVal === "number" && !isNaN(memVal)) {
        const boundLabel = memVal >= 50.0 
          ? `<strong style="color: #f59e0b;">${memVal.toFixed(1)}% (Memory-Bound)</strong>` 
          : `<strong style="color: #10b981;">${(100.0 - memVal).toFixed(1)}% (Compute-Bound)</strong>`;
        boundRow = `<div class="tooltip-row"><span>Cuello de Botella:</span> ${boundLabel}</div>`;
      }
    }

    let extraHtml = "";
    if (block.block_type === "calc" && block.sub_ops && block.sub_ops.length > 0) {
      extraHtml += `<div class="tooltip-subtable-title">Desglose de Micro-Operaciones:</div>`;
      extraHtml += `<table class="tooltip-table">
        <thead><tr><th>Op</th><th>Duración</th><th>% Mem</th></tr></thead>
        <tbody>`;
      block.sub_ops.forEach(sub => {
        const subMemVal = sub.mem_pct ?? sub.mem_bound_pct;
        const subMemStr = typeof subMemVal === "number" && !isNaN(subMemVal) ? `${subMemVal.toFixed(1)}%` : "-";
        extraHtml += `<tr>
          <td><strong>${sub.name}</strong></td>
          <td>${formatSimUnit(sub.duration_ns)}</td>
          <td>${subMemStr}</td>
        </tr>`;
      });
      extraHtml += `</tbody></table>`;
    } else if (block.local_packets !== undefined && block.local_packets > 0) {
      extraHtml += `
        <div class="tooltip-metric-grid">
          <div><span class="label">Paquetes Locales:</span> <strong>${block.local_packets}</strong></div>
          <div><span class="label">Flits Locales:</span> <strong>${block.local_flits}</strong></div>
          <div><span class="label">Lat. Media NoC:</span> <strong>${block.avg_lat_cycles ? block.avg_lat_cycles.toFixed(1) : '-'} c</strong></div>
          <div><span class="label">Throughput:</span> <strong>${block.throughput_flits_per_cycle ? block.throughput_flits_per_cycle.toFixed(2) : '-'} f/c</strong></div>
        </div>
      `;
    }

    this.tooltip.innerHTML = `
      <div class="tooltip-header">
        <span class="badge ${badgeClass}">${typeName}</span>
        <span class="tooltip-gpu">GPU ${gpuIdx} | Capa ${block.layer !== undefined ? block.layer : '-'}</span>
      </div>
      <div class="tooltip-body">
        <div class="tooltip-row"><span>Título:</span> <strong>${block.title}</strong></div>
        <div class="tooltip-row"><span>Intervalo:</span> <code>${formatSimUnit(block.start_ns)} ➔ ${formatSimUnit(block.end_ns)}</code></div>
        <div class="tooltip-row"><span>Duración Total:</span> <strong class="highlight-val">${formatSimUnit(block.duration_ns)}</strong></div>
        ${boundRow}
        ${extraHtml}
      </div>
    `;

    this.tooltip.classList.remove("hidden");

    // Position tooltip safely inside window
    const tipRect = this.tooltip.getBoundingClientRect();
    let left = clientX + 15;
    let top = clientY + 15;

    if (left + tipRect.width > window.innerWidth - 10) {
      left = clientX - tipRect.width - 15;
    }
    if (top + tipRect.height > window.innerHeight - 10) {
      top = window.innerHeight - tipRect.height - 10;
    }

    this.tooltip.style.left = `${Math.max(10, left)}px`;
    this.tooltip.style.top = `${Math.max(10, top)}px`;
  }

  hideTooltip() {
    if (this.tooltip) {
      this.tooltip.classList.add("hidden");
    }
  }

  render() {
    if (!this.canvas) return;
    const { width, height, ctx } = setupHiDPICanvas(this.canvas);
    const t = getCanvasTheme();
    this.canvas.style.cursor = "crosshair";

    // Clear background
    ctx.fillStyle = t.bg;
    ctx.fillRect(0, 0, width, height);

    if (!this.data) {
      ctx.fillStyle = t.textMuted;
      ctx.font = "14px JetBrains Mono, monospace";
      ctx.textAlign = "center";
      ctx.fillText("No hay datos cargados para el Cronograma GPU.", width / 2, height / 2);
      return;
    }

    const plotWidth = width - this.marginLeft - this.marginRight;
    const plotHeight = height - this.headerHeight - this.footerHeight;
    const numGpus = this.data.num_gpus || 1;
    const trackHeight = plotHeight / numGpus;

    const span = this.viewEndNs - this.viewStartNs;
    if (span <= 0) return;

    // 1. Time axis header
    this.drawTimeAxis(ctx, width, plotWidth, span, t);

    // 2. Draw GPU Tracks and Blocks
    for (let g = 0; g < numGpus; g++) {
      const trackY = this.headerHeight + g * trackHeight;

      // Track background alternation
      ctx.fillStyle = (g % 2 === 0) ? t.altRowBg : "transparent";
      ctx.fillRect(this.marginLeft, trackY, plotWidth, trackHeight);

      // Track horizontal border
      ctx.strokeStyle = t.trackLine;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, trackY + trackHeight);
      ctx.lineTo(width, trackY + trackHeight);
      ctx.stroke();

      // Track Label on Left
      ctx.fillStyle = t.textSecondary;
      ctx.font = "12px JetBrains Mono, monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`GPU ${g}`, this.marginLeft - 12, trackY + trackHeight / 2);

      // Render blocks on this track
      const blocks = this.data.tracks[g] || [];
      for (let i = 0; i < blocks.length; i++) {
        const b = blocks[i];
        if (b.end_ns < this.viewStartNs || b.start_ns > this.viewEndNs) continue;

        const x1 = this.marginLeft + ((Math.max(b.start_ns, this.viewStartNs) - this.viewStartNs) / span) * plotWidth;
        const x2 = this.marginLeft + ((Math.min(b.end_ns, this.viewEndNs) - this.viewStartNs) / span) * plotWidth;
        const bWidth = Math.max(1, x2 - x1);
        const bY = trackY + 3;
        const bH = trackHeight - 6;

        this.drawBlock(ctx, b, x1, bY, bWidth, bH, span, plotWidth, t);
      }
    }

    // 3. Draw iteration markers (dividing lines across tracks in full simulation view)
    if (this.data && this.data.iteration_markers && this.data.iteration_markers.length > 1) {
      this.data.iteration_markers.forEach(m => {
        if (m.start_ns > this.minTimeNs && m.start_ns <= this.viewEndNs) {
          const x = this.marginLeft + ((m.start_ns - this.viewStartNs) / span) * plotWidth;
          if (x >= this.marginLeft && x <= this.marginLeft + plotWidth) {
            ctx.save();
            ctx.setLineDash([6, 4]);
            ctx.strokeStyle = t.iterMarker;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(x, this.headerHeight);
            ctx.lineTo(x, height - this.footerHeight);
            ctx.stroke();

            // Iteration badge in header
            ctx.fillStyle = t.iterMarker;
            ctx.fillRect(x - 30, 4, 60, 18);
            ctx.fillStyle = t.iterMarkerText;
            ctx.font = "bold 9px JetBrains Mono, monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(`Iter ${m.iter}`, x, 13);
            ctx.restore();
          }
        }
      });
    }

    // 4. Synchronized vertical crosshair line
    if (this.crosshairX !== null && this.crosshairX !== undefined &&
        this.crosshairX >= this.marginLeft && this.crosshairX <= this.marginLeft + plotWidth) {
      ctx.save();
      ctx.strokeStyle = t.crosshair;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(this.crosshairX, this.headerHeight);
      ctx.lineTo(this.crosshairX, height - this.footerHeight);
      ctx.stroke();

      if (this.crosshairNs !== null) {
        ctx.fillStyle = t.crosshairBadgeBg;
        ctx.fillRect(this.crosshairX - 32, this.headerHeight - 20, 64, 16);
        ctx.fillStyle = t.crosshairBadgeText;
        ctx.font = "bold 9px JetBrains Mono, monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(formatSimUnit(this.crosshairNs), this.crosshairX, this.headerHeight - 12);
      }
      ctx.restore();
    }
  }

  drawTimeAxis(ctx, width, plotWidth, span, theme) {
    const themePal = theme || getCanvasTheme();
    ctx.fillStyle = themePal.headerBg;
    ctx.fillRect(0, 0, width, this.headerHeight);

    ctx.strokeStyle = themePal.axisLine;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, this.headerHeight);
    ctx.lineTo(width, this.headerHeight);
    ctx.stroke();

    // Determine nice tick step
    const rawStep = span / 8;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    let tickStepNs = magnitude;
    if (rawStep / magnitude >= 5) tickStepNs = 5 * magnitude;
    else if (rawStep / magnitude >= 2) tickStepNs = 2 * magnitude;

    const firstTick = Math.ceil(this.viewStartNs / tickStepNs) * tickStepNs;

    ctx.fillStyle = themePal.textSecondary;
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";

    for (let t = firstTick; t <= this.viewEndNs; t += tickStepNs) {
      const x = this.marginLeft + ((t - this.viewStartNs) / span) * plotWidth;
      
      // Tick mark
      ctx.strokeStyle = themePal.tickMark;
      ctx.beginPath();
      ctx.moveTo(x, this.headerHeight - 6);
      ctx.lineTo(x, this.headerHeight);
      ctx.stroke();

      // Vertical guide line across plot
      ctx.strokeStyle = themePal.gridLine;
      ctx.beginPath();
      ctx.moveTo(x, this.headerHeight);
      ctx.lineTo(x, this.canvas.height);
      ctx.stroke();

      // Tick label
      ctx.fillStyle = themePal.textSecondary;
      ctx.fillText(formatSimUnit(t, true), x, this.headerHeight - 8);
    }
  }

  drawBlock(ctx, b, x, y, w, h, span, plotWidth, theme) {
    const themePal = theme || getCanvasTheme();
    // Semantic block color
    let fillColor = themePal.calcFill;
    let strokeColor = themePal.calcStroke;
    
    if (b.block_type === "scatter") {
      fillColor = themePal.scatterFill;
      strokeColor = themePal.scatterStroke;
    } else if (b.block_type === "gather") {
      fillColor = themePal.gatherFill;
      strokeColor = themePal.gatherStroke;
    } else if (b.block_type === "all_reduce") {
      fillColor = themePal.allreduceFill;
      strokeColor = themePal.allreduceStroke;
    } else if (b.block_type === "stall") {
      fillColor = themePal.stallFill;
      strokeColor = themePal.stallStroke;
    }

    // Fill block
    ctx.fillStyle = fillColor;
    ctx.fillRect(x, y, w, h);

    // Border
    if (w > 2) {
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, w, h);
    }

    // Sub-operation dashed lines inside calc blocks
    if (b.block_type === "calc" && b.sub_ops && b.sub_ops.length > 1 && w > 30) {
      ctx.save();
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = themePal.subOpDash;
      ctx.lineWidth = 1;

      b.sub_ops.forEach(sub => {
        if (sub.start_ns > b.start_ns && sub.start_ns < b.end_ns) {
          const subX = this.marginLeft + ((sub.start_ns - this.viewStartNs) / span) * plotWidth;
          if (subX >= x && subX <= x + w) {
            ctx.beginPath();
            ctx.moveTo(subX, y);
            ctx.lineTo(subX, y + h);
            ctx.stroke();
          }
        }
      });
      ctx.restore();
    }

    // Text labels if block is wide enough
    if (w >= 35) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(x + 2, y, w - 4, h);
      ctx.clip();

      if (b.block_type === "calc") ctx.fillStyle = themePal.calcText;
      else if (b.block_type === "scatter") ctx.fillStyle = themePal.scatterText;
      else ctx.fillStyle = themePal.blockLightText;

      ctx.font = "bold 10px JetBrains Mono, monospace";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";

      let label = b.macro_op || b.title || "";
      if (b.layer !== undefined && b.layer >= 0 && !label.startsWith("L" + b.layer) && !label.startsWith("Layer " + b.layer)) {
        label = `L${b.layer} | ${label}`;
      }

      if (h >= 24 && w >= 60) {
        // Two lines
        ctx.fillText(label, x + 4, y + h / 2 - 5);
        ctx.font = "9px JetBrains Mono, monospace";
        ctx.fillText(formatSimUnit(b.duration_ns, true), x + 4, y + h / 2 + 6);
      } else {
        // Single line
        ctx.fillText(label, x + 4, y + h / 2);
      }

      ctx.restore();
    }
  }
}

/* ==========================================================================
   2. PacketFlightCanvas (Sub-vista B: Visualizador de Paquetes en Vuelo)
   ========================================================================== */
class PacketFlightCanvas {
  constructor(canvasEl, tooltipEl, onPageChange) {
    this.canvas = canvasEl;
    this.tooltip = tooltipEl;
    this.onPageChange = onPageChange;

    this.packetsData = null; // response from /api/results/packets
    this.hoveredPacket = null;

    this.marginLeft = 110;
    this.marginRight = 30;
    this.headerHeight = 40;
    this.footerHeight = 40;

    this.bindEvents();
  }

  bindEvents() {
    this.canvas.addEventListener("mousemove", (e) => this.handleMouseMove(e));
    this.canvas.addEventListener("mouseleave", () => this.hideTooltip());
    window.addEventListener("resize", () => this.render());
  }

  loadData(packetsResponse) {
    this.packetsData = packetsResponse;
    this.render();
  }

  handleMouseMove(e) {
    if (!this.packetsData || !this.packetsData.packets || this.packetsData.packets.length === 0) {
      this.hideTooltip();
      return;
    }

    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (mouseX < this.marginLeft || mouseX > rect.width - this.marginRight ||
        mouseY < this.headerHeight || mouseY > rect.height - this.footerHeight) {
      this.hideTooltip();
      return;
    }

    const packets = this.packetsData.packets;
    const plotHeight = rect.height - this.headerHeight - this.footerHeight;
    const rowHeight = plotHeight / packets.length;

    const rowIdx = Math.floor((mouseY - this.headerHeight) / rowHeight);
    if (rowIdx >= 0 && rowIdx < packets.length) {
      const pkt = packets[rowIdx];
      this.showTooltip(pkt, e.clientX, e.clientY);
    } else {
      this.hideTooltip();
    }
  }

  showTooltip(pkt, clientX, clientY) {
    if (!this.tooltip) return;

    const clkNs = this.packetsData.clock_period_ns || 1.0;
    const queueNs = pkt.queue_delay_cycles * clkNs;
    const flightNs = pkt.flight_cycles * clkNs;
    const totalNs = pkt.total_latency_cycles * clkNs;

    this.tooltip.innerHTML = `
      <div class="tooltip-header">
        <span class="badge badge-scatter">PID #${pkt.pid}</span>
        <span class="tooltip-gpu">GPU ${pkt.src} → GPU ${pkt.dst}</span>
      </div>
      <div class="tooltip-body">
        <div class="tooltip-row"><span>Operación / Tipo:</span> <strong>${pkt.op_type || 'Colectiva MoE'}</strong></div>
        <div class="tooltip-row"><span>Flits Totales:</span> <strong>${pkt.flits} flits</strong></div>
        <hr class="tooltip-divider">
        <div class="tooltip-row"><span style="color:var(--warning);font-weight:600;">Retardo en Cola:</span> <strong>${pkt.queue_delay_cycles.toLocaleString()} c (${formatTimeNs(queueNs)})</strong></div>
        <div class="tooltip-row"><span style="color:var(--accent);font-weight:600;">Vuelo NoC (Travesía):</span> <strong>${pkt.flight_cycles.toLocaleString()} c (${formatTimeNs(flightNs)})</strong></div>
        <div class="tooltip-row"><span>Latencia de Paquete:</span> <strong class="highlight-val">${pkt.total_latency_cycles.toLocaleString()} c (${formatTimeNs(totalNs)})</strong></div>
        <hr class="tooltip-divider">
        <div class="tooltip-row"><span>Ciclo Creación:</span> <code>${pkt.creation_cycle.toLocaleString()}</code></div>
        <div class="tooltip-row"><span>Ciclo Inyección:</span> <code>${pkt.inject_cycle.toLocaleString()}</code></div>
        <div class="tooltip-row"><span>Ciclo Recepción:</span> <code>${pkt.receive_cycle.toLocaleString()}</code></div>
      </div>
    `;

    this.tooltip.classList.remove("hidden");

    const tipRect = this.tooltip.getBoundingClientRect();
    let left = clientX + 15;
    let top = clientY + 15;

    if (left + tipRect.width > window.innerWidth - 10) {
      left = clientX - tipRect.width - 15;
    }
    if (top + tipRect.height > window.innerHeight - 10) {
      top = window.innerHeight - tipRect.height - 10;
    }

    this.tooltip.style.left = `${Math.max(10, left)}px`;
    this.tooltip.style.top = `${Math.max(10, top)}px`;
  }

  hideTooltip() {
    if (this.tooltip) {
      this.tooltip.classList.add("hidden");
    }
  }

  render() {
    if (!this.canvas) return;
    const { width, height, ctx } = setupHiDPICanvas(this.canvas);
    const t = getCanvasTheme();

    ctx.fillStyle = t.bg;
    ctx.fillRect(0, 0, width, height);

    if (!this.packetsData || !this.packetsData.packets || this.packetsData.packets.length === 0) {
      ctx.fillStyle = t.textMuted;
      ctx.font = "14px JetBrains Mono, monospace";
      ctx.textAlign = "center";
      ctx.fillText("No hay paquetes disponibles en este rango o la simulación no tuvo SIM_DEBUG_PIDS activado.", width / 2, height / 2);
      return;
    }

    const packets = this.packetsData.packets;
    const plotWidth = width - this.marginLeft - this.marginRight;
    const plotHeight = height - this.headerHeight - this.footerHeight;
    const clkNs = this.packetsData.clock_period_ns || 1.0;

    // Determine min and max BookSim2 cycles in this window
    let minCycle = Infinity;
    let maxCycle = -Infinity;
    packets.forEach(p => {
      if (p.creation_cycle < minCycle) minCycle = p.creation_cycle;
      if (p.receive_cycle > maxCycle) maxCycle = p.receive_cycle;
    });

    if (minCycle === Infinity) { minCycle = 0; maxCycle = 1000; }
    // Add small margin around cycles
    const cycleSpan = Math.max(1, (maxCycle - minCycle) * 1.05);
    const startCycle = Math.max(0, minCycle - cycleSpan * 0.02);
    const endCycle = startCycle + cycleSpan;

    // 1. Subtle background collective bands
    if (this.packetsData.collective_phases) {
      this.packetsData.collective_phases.forEach(phase => {
        if (phase.end_cycle >= startCycle && phase.start_cycle <= endCycle) {
          const x1 = this.marginLeft + ((Math.max(phase.start_cycle, startCycle) - startCycle) / cycleSpan) * plotWidth;
          const x2 = this.marginLeft + ((Math.min(phase.end_cycle, endCycle) - startCycle) / cycleSpan) * plotWidth;
          
          let bandColor = t.phaseScatter;
          if (phase.op_type === "gather") bandColor = t.phaseGather;
          else if (phase.op_type === "all_reduce") bandColor = t.phaseAllreduce;

          ctx.fillStyle = bandColor;
          ctx.fillRect(x1, this.headerHeight, Math.max(1, x2 - x1), plotHeight);
        }
      });
    }

    // 2. Dual Axes (Top: ns, Bottom: BookSim2 cycles)
    this.drawDualAxes(ctx, width, height, plotWidth, startCycle, endCycle, cycleSpan, clkNs, t);

    // 3. Render Packet Gantt bars
    const rowHeight = plotHeight / packets.length;

    packets.forEach((p, idx) => {
      const y = this.headerHeight + idx * rowHeight;
      const barH = Math.max(2, rowHeight - 2);

      // Alternating row background
      if (idx % 2 === 0) {
        ctx.fillStyle = t.altRowBg;
        ctx.fillRect(0, y, width, rowHeight);
      }

      // Left label: PID and nodes
      ctx.fillStyle = t.textSecondary;
      ctx.font = "10px JetBrains Mono, monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`#${p.pid} G${p.src}->G${p.dst}`, this.marginLeft - 8, y + rowHeight / 2);

      // Segment 1: Queueing Delay (Orange)
      const xCreate = this.marginLeft + ((p.creation_cycle - startCycle) / cycleSpan) * plotWidth;
      const xInject = this.marginLeft + ((p.inject_cycle - startCycle) / cycleSpan) * plotWidth;
      const queueW = Math.max(1, xInject - xCreate);

      ctx.fillStyle = t.queueFill;
      ctx.fillRect(xCreate, y + 1, queueW, barH);

      // Segment 2: NoC Flight Time (Blue)
      const xReceive = this.marginLeft + ((p.receive_cycle - startCycle) / cycleSpan) * plotWidth;
      const flightW = Math.max(1, xReceive - xInject);

      ctx.fillStyle = t.flightFill;
      ctx.fillRect(xInject, y + 1, flightW, barH);
    });
  }

  drawDualAxes(ctx, width, height, plotWidth, startCycle, endCycle, cycleSpan, clkNs, theme) {
    const t = theme || getCanvasTheme();
    // Top Header Box (Nanoseconds)
    ctx.fillStyle = t.headerBg;
    ctx.fillRect(0, 0, width, this.headerHeight);
    ctx.strokeStyle = t.axisLine;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, this.headerHeight);
    ctx.lineTo(width, this.headerHeight);
    ctx.stroke();

    // Bottom Footer Box (BookSim2 Cycles)
    const footerY = height - this.footerHeight;
    ctx.fillStyle = t.headerBg;
    ctx.fillRect(0, footerY, width, this.footerHeight);
    ctx.beginPath();
    ctx.moveTo(0, footerY);
    ctx.lineTo(width, footerY);
    ctx.stroke();

    // Axis titles
    ctx.fillStyle = t.accent;
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText("Eje Superior: Tiempo Global (ns)", 10, this.headerHeight / 2);

    ctx.fillStyle = t.iterMarker;
    ctx.fillText("Eje Inferior: Ciclos BookSim2", 10, footerY + this.footerHeight / 2);

    // Ticks calculation
    const rawStep = cycleSpan / 8;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    let tickStep = magnitude;
    if (rawStep / magnitude >= 5) tickStep = 5 * magnitude;
    else if (rawStep / magnitude >= 2) tickStep = 2 * magnitude;

    const firstTick = Math.ceil(startCycle / tickStep) * tickStep;

    ctx.textAlign = "center";
    for (let c = firstTick; c <= endCycle; c += tickStep) {
      const x = this.marginLeft + ((c - startCycle) / cycleSpan) * plotWidth;

      // Top Tick (ns)
      ctx.fillStyle = t.textSecondary;
      ctx.font = "10px JetBrains Mono, monospace";
      ctx.fillText(formatTimeNs(c * clkNs), x, this.headerHeight - 8);

      // Bottom Tick (cycles)
      ctx.fillText(`${Math.round(c).toLocaleString()} c`, x, footerY + 18);

      // Vertical guide line
      ctx.strokeStyle = t.gridLine;
      ctx.beginPath();
      ctx.moveTo(x, this.headerHeight);
      ctx.lineTo(x, footerY);
      ctx.stroke();
    }
  }
}

/* ==========================================================================
   3. HybridPacketCanvas (Panel Derecho: Viewport Virtualizado con Cabecera Sticky)
   ========================================================================== */
class HybridPacketCanvas {
  constructor(canvasEl, headerCanvasEl, scrollContainerEl, spacerEl, visibleInfoEl, tooltipEl, onHoverPacket) {
    this.canvas = canvasEl;
    this.headerCanvas = headerCanvasEl;
    this.scrollContainer = scrollContainerEl;
    this.spacerEl = spacerEl;
    this.visibleInfoEl = visibleInfoEl;
    this.tooltip = tooltipEl;
    this.onHoverPacket = onHoverPacket || null;

    this.packetsData = null; // { packets: [...] }
    this.viewStartNs = 0;
    this.viewEndNs = 20000;
    this.minTimeNs = 0;
    this.maxTimeNs = 20000;

    this.ROW_HEIGHT = 20;
    this.marginLeft = 85;
    this.marginRight = 20;
    this.headerHeight = 36;

    this.hoveredRowIdx = -1;
    this.crosshairX = null;
    this.crosshairNs = null;

    this.bindEvents();
  }

  bindEvents() {
    if (this.scrollContainer) {
      this.scrollContainer.addEventListener("scroll", () => {
        this.drawVisibleSlice();
      }, { passive: true });
    }

    window.addEventListener("resize", () => {
      this.render();
    });
  }

  loadData(packetsResponse, viewStartNs, viewEndNs) {
    if (Array.isArray(packetsResponse)) {
      this.packetsData = { packets: packetsResponse };
    } else {
      this.packetsData = packetsResponse || { packets: [] };
    }
    if (viewStartNs !== undefined) this.viewStartNs = viewStartNs;
    if (viewEndNs !== undefined) this.viewEndNs = viewEndNs;

    const packets = this.packetsData.packets || [];
    const totalPackets = packets.length;
    const neededH = Math.max(600, totalPackets * this.ROW_HEIGHT);

    if (this.spacerEl) {
      this.spacerEl.style.height = `${neededH}px`;
    }

    this.render();
  }

  setCrosshair(x, ns) {
    this.crosshairX = x;
    this.crosshairNs = ns;
    this.drawHeaderAxis();
    this.drawVisibleSlice();
  }

  clearCrosshair() {
    if (this.crosshairX !== null) {
      this.crosshairX = null;
      this.crosshairNs = null;
      this.drawHeaderAxis();
      this.drawVisibleSlice();
    }
  }

  render() {
    this.drawHeaderAxis();
    this.drawVisibleSlice();
  }

  drawHeaderAxis() {
    if (!this.headerCanvas) return;
    const { width, height, ctx } = setupHiDPICanvas(this.headerCanvas);
    const tTheme = getCanvasTheme();

    // Background
    ctx.fillStyle = tTheme.headerBg;
    ctx.fillRect(0, 0, width, height);

    // Bottom border
    ctx.strokeStyle = tTheme.axisLine;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, height - 0.5);
    ctx.lineTo(width, height - 0.5);
    ctx.stroke();

    const span = this.viewEndNs - this.viewStartNs;
    if (span <= 0) return;

    const plotWidth = width - this.marginLeft - this.marginRight;
    if (plotWidth <= 0) return;

    // Time Ticks
    const targetTicks = Math.max(4, Math.floor(plotWidth / 90));
    const rawStep = span / targetTicks;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    let tickStep = magnitude;
    if (rawStep / magnitude >= 5) tickStep = 5 * magnitude;
    else if (rawStep / magnitude >= 2) tickStep = 2 * magnitude;

    const firstTick = Math.ceil(this.viewStartNs / tickStep) * tickStep;

    ctx.fillStyle = tTheme.textSecondary;
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    for (let t = firstTick; t <= this.viewEndNs; t += tickStep) {
      const x = this.marginLeft + ((t - this.viewStartNs) / span) * plotWidth;
      if (x >= this.marginLeft && x <= width - this.marginRight) {
        // Tick mark
        ctx.strokeStyle = tTheme.tickMark;
        ctx.beginPath();
        ctx.moveTo(x, height - 6);
        ctx.lineTo(x, height);
        ctx.stroke();

        // Label
        ctx.fillText(formatSimUnit(t), x, 16);
      }
    }

    // Crosshair badge in header
    if (this.crosshairX !== null && this.crosshairX >= this.marginLeft && this.crosshairX <= width - this.marginRight) {
      ctx.save();
      ctx.fillStyle = tTheme.crosshairBadgeBg;
      ctx.fillRect(this.crosshairX - 32, 8, 64, 18);
      ctx.fillStyle = tTheme.crosshairBadgeText;
      ctx.font = "bold 9px JetBrains Mono, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(formatSimUnit(this.crosshairNs), this.crosshairX, 17);
      ctx.restore();
    }
  }

  drawVisibleSlice() {
    if (!this.canvas || !this.scrollContainer) return;
    const tTheme = getCanvasTheme();

    const viewportH = 602;
    if (this.canvas.style.height !== `${viewportH}px`) {
      this.canvas.style.height = `${viewportH}px`;
    }

    const { width, height, ctx } = setupHiDPICanvas(this.canvas);
    this.canvas.style.cursor = "crosshair";

    // Clear background
    ctx.fillStyle = tTheme.bg;
    ctx.fillRect(0, 0, width, height);

    const packets = this.packetsData && this.packetsData.packets ? this.packetsData.packets : [];
    const totalPackets = packets.length;

    if (totalPackets === 0) {
      ctx.fillStyle = tTheme.textMuted;
      ctx.font = "12px JetBrains Mono, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("No hay paquetes en tránsito dentro de esta ventana de tiempo.", width / 2, height / 2);
      if (this.visibleInfoEl) {
        this.visibleInfoEl.textContent = "Mostrando paquetes 0 de 0";
        this.visibleInfoEl.classList.remove("is-truncated");
      }
      return;
    }

    const scrollTop = this.scrollContainer.scrollTop;
    const firstIdx = Math.max(0, Math.floor(scrollTop / this.ROW_HEIGHT));
    const lastIdx = Math.min(totalPackets - 1, Math.ceil((scrollTop + viewportH) / this.ROW_HEIGHT));

    if (this.visibleInfoEl) {
      const isTruncated = Boolean(this.packetsData && this.packetsData.truncated);
      if (isTruncated) {
        const totalInWin = this.packetsData.total_in_window != null ? this.packetsData.total_in_window : totalPackets;
        const retCount = this.packetsData.returned != null ? this.packetsData.returned : totalPackets;
        this.visibleInfoEl.textContent = `Mostrando ${retCount.toLocaleString()} de ${totalInWin.toLocaleString()} paquetes (muestreo macro — haz zoom para ver el 100% exacto)`;
        this.visibleInfoEl.classList.add("is-truncated");
      } else {
        this.visibleInfoEl.textContent = `Mostrando paquetes ${firstIdx + 1}–${lastIdx + 1} de ${totalPackets.toLocaleString()}`;
        this.visibleInfoEl.classList.remove("is-truncated");
      }
    }

    const plotWidth = width - this.marginLeft - this.marginRight;
    const span = this.viewEndNs - this.viewStartNs;
    if (span <= 0 || plotWidth <= 0) return;

    const barH = 14;

    for (let i = firstIdx; i <= lastIdx; i++) {
      const p = packets[i];
      const y = (i * this.ROW_HEIGHT) - scrollTop;

      // Row background
      if (i === this.hoveredRowIdx) {
        ctx.fillStyle = tTheme.hoverRowBg;
        ctx.fillRect(0, y, width, this.ROW_HEIGHT);
      } else if (i % 2 === 0) {
        ctx.fillStyle = tTheme.altRowBg;
        ctx.fillRect(0, y, width, this.ROW_HEIGHT);
      }

      // Left label: PID & GPU Nodes
      ctx.fillStyle = (i === this.hoveredRowIdx) ? tTheme.accent : tTheme.textSecondary;
      ctx.font = "9px JetBrains Mono, monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`#${p.pid} G${p.src}->G${p.dst}`, this.marginLeft - 6, y + this.ROW_HEIGHT / 2);

      // Segment 1: Queueing Delay in orange
      const xStart = this.marginLeft + ((p.pkt_start_ns - this.viewStartNs) / span) * plotWidth;
      const xInject = this.marginLeft + ((p.pkt_inject_ns - this.viewStartNs) / span) * plotWidth;
      const queueW = Math.max(3, xInject - xStart);

      ctx.fillStyle = tTheme.queueFill;
      ctx.fillRect(xStart, y + 3, queueW, barH);

      // Segment 2: NoC Flight in blue
      const xEnd = this.marginLeft + ((p.pkt_end_ns - this.viewStartNs) / span) * plotWidth;
      const flightW = Math.max(3, xEnd - xInject);

      ctx.fillStyle = tTheme.flightFill;
      ctx.fillRect(xInject, y + 3, flightW, barH);
    }

    // Vertical crosshair guide
    if (this.crosshairX !== null && this.crosshairX >= this.marginLeft && this.crosshairX <= width - this.marginRight) {
      ctx.save();
      ctx.strokeStyle = tTheme.crosshair;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(this.crosshairX, 0);
      ctx.lineTo(this.crosshairX, height);
      ctx.stroke();
      ctx.restore();
    }
  }

  getPacketAt(clientX, clientY) {
    if (!this.packetsData || !this.packetsData.packets || this.packetsData.packets.length === 0) return null;
    const packets = this.packetsData.packets;
    const rect = this.canvas.getBoundingClientRect();
    const localX = clientX - rect.left;
    const localY = clientY - rect.top;

    if (localY < 0 || localY > rect.height) return null;

    const virtualY = this.scrollContainer.scrollTop + localY;
    const idx = Math.floor(virtualY / this.ROW_HEIGHT);

    if (idx >= 0 && idx < packets.length) {
      return { packet: packets[idx], rowIdx: idx };
    }
    return null;
  }

  showTooltip(pkt, clientX, clientY) {
    if (!this.tooltip) return;

    const queueC = pkt.queue_delay_cycles;
    const flightC = pkt.flight_cycles;
    const totalC = pkt.total_latency_cycles;
    const bytes = (pkt.flits || 9) * 16;

    this.tooltip.innerHTML = `
      <div class="tooltip-header">
        <span class="badge badge-scatter">PID #${pkt.pid}</span>
        <span class="tooltip-gpu">GPU ${pkt.src} → GPU ${pkt.dst}</span>
      </div>
      <div class="tooltip-body">
        <div class="tooltip-row"><span>Operación / Tipo:</span> <strong>${pkt.op_type} Nº${pkt.op_idx || 1}</strong></div>
        <div class="tooltip-row"><span>Carga Útil:</span> <strong>${pkt.flits} flits (${bytes} bytes)</strong></div>
        <hr class="tooltip-divider">
        <div class="tooltip-row"><span style="color:var(--warning);font-weight:600;">Retardo en Cola NIC:</span> <strong>${Math.round(queueC).toLocaleString()} c (${formatSimUnit(queueC)})</strong></div>
        <div class="tooltip-row"><span style="color:var(--accent);font-weight:600;">Vuelo NoC (Travesía):</span> <strong>${Math.round(flightC).toLocaleString()} c (${formatSimUnit(flightC)})</strong></div>
        <div class="tooltip-row"><span>Latencia de Paquete:</span> <strong class="highlight-val">${Math.round(totalC).toLocaleString()} c (${formatSimUnit(totalC)})</strong></div>
        <hr class="tooltip-divider">
        <div class="tooltip-row"><span>Ciclo / T Creación:</span> <code>${formatSimUnit(pkt.pkt_start_ns)}</code></div>
        <div class="tooltip-row"><span>Ciclo / T Inyección:</span> <code>${formatSimUnit(pkt.pkt_inject_ns)}</code></div>
        <div class="tooltip-row"><span>Ciclo / T Recepción:</span> <code>${formatSimUnit(pkt.pkt_end_ns)}</code></div>
      </div>
    `;

    this.tooltip.classList.remove("hidden");

    const tipRect = this.tooltip.getBoundingClientRect();
    let left = clientX + 15;
    let top = clientY + 15;

    if (left + tipRect.width > window.innerWidth - 10) {
      left = clientX - tipRect.width - 15;
    }
    if (top + tipRect.height > window.innerHeight - 10) {
      top = window.innerHeight - tipRect.height - 10;
    }

    this.tooltip.style.left = `${Math.max(10, left)}px`;
    this.tooltip.style.top = `${Math.max(10, top)}px`;
  }

  hideTooltip() {
    if (this.tooltip) {
      this.tooltip.classList.add("hidden");
    }
  }
}

/* ==========================================================================
   4. HybridSyncController (Gestor de Sincronización Split-Screen)
   ========================================================================== */
class HybridSyncController {
  constructor(optsOrChronoEl, packetsCanvasEl, tooltipEl, fetchPacketsWindowFn, onViewportChange) {
    if (optsOrChronoEl && typeof optsOrChronoEl === "object" && !optsOrChronoEl.tagName) {
      const opts = optsOrChronoEl;
      this.chronoCanvasEl = opts.chronoCanvasEl;
      this.packetsCanvasEl = opts.packetsCanvasEl;
      this.packetsHeaderCanvasEl = opts.packetsHeaderCanvasEl;
      this.packetsScrollContainerEl = opts.packetsScrollContainerEl;
      this.packetsSpacerEl = opts.packetsSpacerEl;
      this.packetsVisibleInfoEl = opts.packetsVisibleInfoEl;
      this.tooltipEl = opts.tooltipEl;
      this.scrubberEl = opts.scrubberEl;
      this.scrubberPosEl = opts.scrubberPosEl;
      this.windowInfoEl = opts.windowInfoEl;
      this.packetBadgeEl = opts.packetBadgeEl;
      this.fetchPacketsWindowFn = opts.fetchPacketsWindowFn;
      this.onViewportChange = opts.onViewportChange || null;
    } else {
      this.chronoCanvasEl = optsOrChronoEl;
      this.packetsCanvasEl = packetsCanvasEl;
      this.packetsHeaderCanvasEl = null;
      this.packetsScrollContainerEl = null;
      this.packetsSpacerEl = null;
      this.packetsVisibleInfoEl = null;
      this.tooltipEl = tooltipEl;
      this.fetchPacketsWindowFn = fetchPacketsWindowFn;
      this.onViewportChange = onViewportChange || null;
    }

    this.chronoCanvas = null;
    this.packetCanvas = null;

    this.viewStartNs = 0;
    this.viewEndNs = 20000;
    this.minTimeNs = 0;
    this.maxTimeNs = 20000;

    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartViewStart = 0;
    this.dragStartViewEnd = 0;

    this.fetchDebounceTimer = null;
    this.fetchAbortController = null;
    this.fetchSeqId = 0;

    this.init();
  }

  loadData(chronoData) {
    this.loadChronogram(chronoData);
  }

  init() {
    this.chronoCanvas = new ChronogramCanvas(
      this.chronoCanvasEl,
      this.tooltipEl,
      (start, end, min, max) => this.onViewportUpdated(start, end, min, max)
    );
    this.chronoCanvas.marginLeft = 85;

    this.packetCanvas = new HybridPacketCanvas(
      this.packetsCanvasEl,
      this.packetsHeaderCanvasEl,
      this.packetsScrollContainerEl,
      this.packetsSpacerEl,
      this.packetsVisibleInfoEl,
      this.tooltipEl
    );
    this.packetCanvas.marginLeft = 85;

    this.bindSharedEvents();
  }

  bindSharedEvents() {
    const handleMove = (e, canvasTarget) => {
      const rect = canvasTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const plotWidth = rect.width - this.chronoCanvas.marginLeft - this.chronoCanvas.marginRight;

      if (x >= this.chronoCanvas.marginLeft && x <= rect.width - this.chronoCanvas.marginRight) {
        const span = this.viewEndNs - this.viewStartNs;
        const mouseNs = this.viewStartNs + ((x - this.chronoCanvas.marginLeft) / plotWidth) * span;

        this.chronoCanvas.setCrosshair(x, mouseNs);
        this.packetCanvas.setCrosshair(x, mouseNs);

        if (canvasTarget === this.packetsCanvasEl) {
          const res = this.packetCanvas.getPacketAt(e.clientX, e.clientY);
          if (res) {
            this.chronoCanvas.hideTooltip();
            const prevRow = this.packetCanvas.hoveredRowIdx;
            this.packetCanvas.hoveredRowIdx = res.rowIdx;
            if (prevRow !== res.rowIdx) {
              this.packetCanvas.drawVisibleSlice();
            }
            this.packetCanvas.showTooltip(res.packet, e.clientX, e.clientY);
          } else {
            if (this.packetCanvas.hoveredRowIdx !== -1) {
              this.packetCanvas.hoveredRowIdx = -1;
              this.packetCanvas.drawVisibleSlice();
            }
            this.packetCanvas.hideTooltip();
          }
        } else if (canvasTarget === this.chronoCanvasEl) {
          if (this.packetCanvas.hoveredRowIdx !== -1) {
            this.packetCanvas.hoveredRowIdx = -1;
            this.packetCanvas.drawVisibleSlice();
          }
          this.packetCanvas.hideTooltip();

          const res = this.chronoCanvas.getBlockAt(x, y);
          if (res) {
            this.chronoCanvas.showTooltip(res.block, res.gpuIdx, e.clientX, e.clientY);
          } else {
            this.chronoCanvas.hideTooltip();
          }
        }
      } else {
        this.chronoCanvas.clearCrosshair();
        this.packetCanvas.clearCrosshair();
        if (this.packetCanvas.hoveredRowIdx !== -1) {
          this.packetCanvas.hoveredRowIdx = -1;
          this.packetCanvas.drawVisibleSlice();
        }
        this.hideTooltip();
        this.chronoCanvas.hideTooltip();
        this.packetCanvas.hideTooltip();
      }
    };

    const handleLeave = () => {
      this.chronoCanvas.clearCrosshair();
      this.packetCanvas.clearCrosshair();
      if (this.packetCanvas.hoveredRowIdx !== -1) {
        this.packetCanvas.hoveredRowIdx = -1;
        this.packetCanvas.drawVisibleSlice();
      }
      this.hideTooltip();
      this.chronoCanvas.hideTooltip();
      this.packetCanvas.hideTooltip();
    };

    this.chronoCanvasEl.addEventListener("mousemove", (e) => handleMove(e, this.chronoCanvasEl));
    this.packetsCanvasEl.addEventListener("mousemove", (e) => handleMove(e, this.packetsCanvasEl));

    this.chronoCanvasEl.addEventListener("mouseleave", handleLeave);
    this.packetsCanvasEl.addEventListener("mouseleave", handleLeave);

    const handleWheelChrono = (e) => {
      e.preventDefault();
      const rect = this.chronoCanvasEl.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const plotWidth = rect.width - this.chronoCanvas.marginLeft - this.chronoCanvas.marginRight;
      let ratio = 0.5;
      if (x >= this.chronoCanvas.marginLeft && x <= rect.width - this.chronoCanvas.marginRight) {
        ratio = (x - this.chronoCanvas.marginLeft) / plotWidth;
      }
      const factor = e.deltaY > 0 ? 1.15 : 0.85;
      this.zoom(factor, ratio);
    };

    const handleWheelPackets = (e) => {
      if (e.ctrlKey || e.shiftKey || e.altKey) {
        e.preventDefault();
        const rect = this.packetsCanvasEl.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const plotWidth = rect.width - this.chronoCanvas.marginLeft - this.chronoCanvas.marginRight;
        let ratio = 0.5;
        if (x >= this.chronoCanvas.marginLeft && x <= rect.width - this.chronoCanvas.marginRight) {
          ratio = (x - this.chronoCanvas.marginLeft) / plotWidth;
        }
        const factor = e.deltaY > 0 ? 1.15 : 0.85;
        this.zoom(factor, ratio);
      }
    };

    this.chronoCanvasEl.addEventListener("wheel", handleWheelChrono, { passive: false });
    this.packetsCanvasEl.addEventListener("wheel", handleWheelPackets, { passive: false });

    const handleMouseDown = (e, canvasTarget) => {
      const rect = canvasTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (x < this.chronoCanvas.marginLeft) return;

      this.isDragging = true;
      this.dragStartX = e.clientX;
      this.dragStartViewStart = this.viewStartNs;
      this.dragStartViewEnd = this.viewEndNs;
      this.chronoCanvasEl.style.cursor = "grabbing";
    };

    const handleGlobalMouseMove = (e) => {
      if (!this.isDragging) return;
      const rect = this.chronoCanvasEl.getBoundingClientRect();
      const plotWidth = rect.width - this.chronoCanvas.marginLeft - this.chronoCanvas.marginRight;
      if (plotWidth <= 0) return;

      const dx = e.clientX - this.dragStartX;
      const span = this.dragStartViewEnd - this.dragStartViewStart;
      const dt = -(dx / plotWidth) * span;

      let newStart = this.dragStartViewStart + dt;
      let newEnd = this.dragStartViewEnd + dt;

      if (newStart < this.minTimeNs) {
        newStart = this.minTimeNs;
        newEnd = newStart + span;
      }
      if (newEnd > this.maxTimeNs) {
        newEnd = this.maxTimeNs;
        newStart = Math.max(this.minTimeNs, newEnd - span);
      }

      this.updateViewport(newStart, newEnd);
    };

    const handleGlobalMouseUp = () => {
      if (this.isDragging) {
        this.isDragging = false;
        this.chronoCanvasEl.style.cursor = "crosshair";
      }
    };

    this.chronoCanvasEl.addEventListener("mousedown", (e) => handleMouseDown(e, this.chronoCanvasEl));
    window.addEventListener("mousemove", handleGlobalMouseMove);
    window.addEventListener("mouseup", handleGlobalMouseUp);

    if (this.scrubberEl) {
      this.scrubberEl.addEventListener("input", () => {
        const span = this.viewEndNs - this.viewStartNs;
        const maxStart = this.maxTimeNs - span;
        const ratio = this.scrubberEl.value / 1000;
        const newStart = this.minTimeNs + ratio * (maxStart - this.minTimeNs);
        this.updateViewport(newStart, newStart + span);
      });
    }
  }

  loadChronogram(chronoData) {
    this.chronoCanvas.loadData(chronoData);
    this.minTimeNs = chronoData.min_time_ns || 0;
    this.maxTimeNs = chronoData.max_time_ns || 1;
    this.viewStartNs = this.chronoCanvas.viewStartNs;
    this.viewEndNs = this.chronoCanvas.viewEndNs;

    this.packetCanvas.minTimeNs = this.minTimeNs;
    this.packetCanvas.maxTimeNs = this.maxTimeNs;
    this.packetCanvas.viewStartNs = this.viewStartNs;
    this.packetCanvas.viewEndNs = this.viewEndNs;

    this.triggerFetchPackets();
  }

  setWindowPreset(presetUs) {
    if (presetUs === "all") {
      this.updateViewport(this.minTimeNs, this.maxTimeNs);
    } else {
      const windowNs = presetUs * 1000;
      const currentCenter = (this.viewStartNs + this.viewEndNs) / 2;
      let start = currentCenter - windowNs / 2;
      let end = currentCenter + windowNs / 2;

      if (start < this.minTimeNs) {
        start = this.minTimeNs;
        end = start + windowNs;
      }
      if (end > this.maxTimeNs) {
        end = this.maxTimeNs;
        start = Math.max(this.minTimeNs, end - windowNs);
      }
      this.updateViewport(start, end);
    }
  }

  setScrubberRatio(ratio) {
    const span = this.viewEndNs - this.viewStartNs;
    const maxStart = this.maxTimeNs - span;
    if (maxStart > this.minTimeNs) {
      const newStart = this.minTimeNs + ratio * (maxStart - this.minTimeNs);
      this.updateViewport(newStart, newStart + span);
    }
  }

  zoom(factor, centerRatio = 0.5) {
    const currentSpan = this.viewEndNs - this.viewStartNs;
    let newSpan = currentSpan * factor;
    newSpan = Math.max(100, Math.min((this.maxTimeNs - this.minTimeNs) * 1.5, newSpan));

    const centerTime = this.viewStartNs + currentSpan * centerRatio;
    let newStart = centerTime - newSpan * centerRatio;
    let newEnd = newStart + newSpan;

    if (newStart < this.minTimeNs) {
      newStart = this.minTimeNs;
      newEnd = newStart + newSpan;
    }
    if (newEnd > this.maxTimeNs && (newEnd - newStart) <= (this.maxTimeNs - this.minTimeNs)) {
      newEnd = this.maxTimeNs;
      newStart = Math.max(this.minTimeNs, newEnd - newSpan);
    }

    this.updateViewport(newStart, newEnd);
  }

  updateViewport(newStart, newEnd) {
    this.viewStartNs = newStart;
    this.viewEndNs = newEnd;

    this.chronoCanvas.viewStartNs = newStart;
    this.chronoCanvas.viewEndNs = newEnd;
    this.chronoCanvas.render();

    this.packetCanvas.viewStartNs = newStart;
    this.packetCanvas.viewEndNs = newEnd;
    this.packetCanvas.render();

    const span = newEnd - newStart;
    if (this.windowInfoEl) {
      this.windowInfoEl.textContent = `Ventana: ${formatSimUnit(newStart)} ➔ ${formatSimUnit(newEnd)} (${formatSimUnit(span, true)})`;
    }
    if (this.scrubberPosEl) {
      this.scrubberPosEl.textContent = formatSimUnit(newStart);
    }

    const currentSpan = newEnd - newStart;
    const maxStart = this.maxTimeNs - currentSpan;
    if (this.scrubberEl && maxStart > this.minTimeNs) {
      const ratio = (newStart - this.minTimeNs) / (maxStart - this.minTimeNs);
      this.scrubberEl.value = Math.round(ratio * 1000);
    }

    this.triggerFetchPackets();
  }

  onViewportUpdated(start, end, min, max) {
    this.viewStartNs = start;
    this.viewEndNs = end;
    this.minTimeNs = min;
    this.maxTimeNs = max;
    if (this.packetCanvas) {
      this.packetCanvas.viewStartNs = start;
      this.packetCanvas.viewEndNs = end;
      this.packetCanvas.minTimeNs = min;
      this.packetCanvas.maxTimeNs = max;
      this.packetCanvas.render();
    }
    this.triggerFetchPackets();
  }

  cancelPendingFetches() {
    clearTimeout(this.fetchDebounceTimer);
    if (this.fetchAbortController) {
      try {
        this.fetchAbortController.abort();
      } catch (e) {}
      this.fetchAbortController = null;
    }
    this.fetchSeqId += 1;
  }

  triggerFetchPackets() {
    clearTimeout(this.fetchDebounceTimer);
    this.fetchDebounceTimer = setTimeout(async () => {
      if (this.fetchPacketsWindowFn) {
        if (this.fetchAbortController) {
          try {
            this.fetchAbortController.abort();
          } catch (e) {}
        }
        this.fetchAbortController = typeof AbortController !== "undefined" ? new AbortController() : null;
        const seqId = ++this.fetchSeqId;
        const signal = this.fetchAbortController ? this.fetchAbortController.signal : undefined;

        const data = await this.fetchPacketsWindowFn(this.viewStartNs, this.viewEndNs, undefined, signal);
        if (data && seqId === this.fetchSeqId) {
          this.packetCanvas.loadData(data, this.viewStartNs, this.viewEndNs);
          if (this.packetBadgeEl) {
            const count = data.total_in_window || 0;
            const ret = data.returned != null ? data.returned : (data.packets ? data.packets.length : 0);
            if (data.truncated) {
              this.packetBadgeEl.textContent = `${count.toLocaleString()} pkts (muestreo: ${ret.toLocaleString()})`;
              this.packetBadgeEl.classList.add("is-truncated");
            } else {
              this.packetBadgeEl.textContent = `${count.toLocaleString()} paquetes en ventana`;
              this.packetBadgeEl.classList.remove("is-truncated");
            }
          }
        }
      }
    }, 60);
  }

  hideTooltip() {
    if (this.tooltipEl) {
      this.tooltipEl.classList.add("hidden");
    }
  }

  render() {
    this.chronoCanvas.render();
    this.packetCanvas.render();
  }
}

// Export classes to global window
window.ChronogramCanvas = ChronogramCanvas;
window.PacketFlightCanvas = PacketFlightCanvas;
window.HybridPacketCanvas = HybridPacketCanvas;
window.HybridSyncController = HybridSyncController;

