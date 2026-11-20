/**
 * LLM-NoC Co-Simulation Workbench - Interactive HTML5 Canvas Renderers
 * Provides high-performance, on-the-fly rendering for:
 * 1. ChronogramCanvas: GPU cycle-by-cycle causal chronogram (tracks GPU 0..N-1)
 * 2. PacketFlightCanvas: BookSim2 in-flight packet Gantt chart (Queue + Flight)
 */

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

    const plotWidth = rect.width - this.marginLeft - this.marginRight;
    const plotHeight = rect.height - this.headerHeight - this.footerHeight;
    const numGpus = this.data.num_gpus || 1;
    const trackHeight = plotHeight / numGpus;

    const gpuIdx = Math.floor((mouseY - this.headerHeight) / trackHeight);
    if (gpuIdx < 0 || gpuIdx >= numGpus) {
      this.hideTooltip();
      return;
    }

    const span = this.viewEndNs - this.viewStartNs;
    const mouseNs = this.viewStartNs + ((mouseX - this.marginLeft) / plotWidth) * span;

    // Find block on this GPU
    const trackBlocks = this.data.tracks[gpuIdx] || [];
    let foundBlock = null;

    for (let i = 0; i < trackBlocks.length; i++) {
      const b = trackBlocks[i];
      if (mouseNs >= b.start_ns && mouseNs <= b.end_ns) {
        foundBlock = b;
        break;
      }
      if (b.start_ns > mouseNs) break; // Blocks are sorted chronologically
    }

    if (foundBlock) {
      this.showTooltip(foundBlock, gpuIdx, e.clientX, e.clientY);
    } else {
      this.hideTooltip();
    }
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
      typeName = "Stall por Barrera de Sincronización";
    }

    let extraHtml = "";
    if (block.block_type === "calc" && block.sub_ops && block.sub_ops.length > 0) {
      extraHtml += `<div class="tooltip-subtable-title">Desglose de Micro-Operaciones:</div>`;
      extraHtml += `<table class="tooltip-table">
        <thead><tr><th>Op</th><th>Duración</th><th>% Mem</th></tr></thead>
        <tbody>`;
      block.sub_ops.forEach(sub => {
        extraHtml += `<tr>
          <td><strong>${sub.name}</strong></td>
          <td>${formatTimeNs(sub.duration_ns)}</td>
          <td>${sub.mem_pct !== undefined ? sub.mem_pct.toFixed(0) + '%' : '-'}</td>
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
        <div class="tooltip-row"><span>Intervalo:</span> <code>${formatTimeNs(block.start_ns)} ➔ ${formatTimeNs(block.end_ns)}</code></div>
        <div class="tooltip-row"><span>Duración Total:</span> <strong class="highlight-val">${formatTimeNs(block.duration_ns)}</strong></div>
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
    this.canvas.style.cursor = "crosshair";

    // Clear background
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, width, height);

    if (!this.data) {
      ctx.fillStyle = "#64748b";
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
    this.drawTimeAxis(ctx, width, plotWidth, span);

    // 2. Draw GPU Tracks and Blocks
    for (let g = 0; g < numGpus; g++) {
      const trackY = this.headerHeight + g * trackHeight;

      // Track background alternation
      ctx.fillStyle = (g % 2 === 0) ? "rgba(255, 255, 255, 0.015)" : "transparent";
      ctx.fillRect(this.marginLeft, trackY, plotWidth, trackHeight);

      // Track horizontal border
      ctx.strokeStyle = "#1e293b";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, trackY + trackHeight);
      ctx.lineTo(width, trackY + trackHeight);
      ctx.stroke();

      // Track Label on Left
      ctx.fillStyle = "#94a3b8";
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

        this.drawBlock(ctx, b, x1, bY, bWidth, bH, span, plotWidth);
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
            ctx.strokeStyle = "#f59e0b"; // gold / amber
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(x, this.headerHeight);
            ctx.lineTo(x, height - this.footerHeight);
            ctx.stroke();

            // Iteration badge in header
            ctx.fillStyle = "#f59e0b";
            ctx.fillRect(x - 30, 4, 60, 18);
            ctx.fillStyle = "#000";
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
      ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(this.crosshairX, this.headerHeight);
      ctx.lineTo(this.crosshairX, height - this.footerHeight);
      ctx.stroke();

      if (this.crosshairNs !== null) {
        ctx.fillStyle = "#38bdf8";
        ctx.fillRect(this.crosshairX - 32, this.headerHeight - 20, 64, 16);
        ctx.fillStyle = "#000";
        ctx.font = "bold 9px JetBrains Mono, monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(formatTimeNs(this.crosshairNs), this.crosshairX, this.headerHeight - 12);
      }
      ctx.restore();
    }
  }

  drawTimeAxis(ctx, width, plotWidth, span) {
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, width, this.headerHeight);

    ctx.strokeStyle = "#334155";
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

    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";

    for (let t = firstTick; t <= this.viewEndNs; t += tickStepNs) {
      const x = this.marginLeft + ((t - this.viewStartNs) / span) * plotWidth;
      
      // Tick mark
      ctx.strokeStyle = "#475569";
      ctx.beginPath();
      ctx.moveTo(x, this.headerHeight - 6);
      ctx.lineTo(x, this.headerHeight);
      ctx.stroke();

      // Vertical guide line across plot
      ctx.strokeStyle = "rgba(51, 65, 85, 0.3)";
      ctx.beginPath();
      ctx.moveTo(x, this.headerHeight);
      ctx.lineTo(x, this.canvas.height);
      ctx.stroke();

      // Tick label
      ctx.fillText(formatTimeNs(t), x, this.headerHeight - 8);
    }
  }

  drawBlock(ctx, b, x, y, w, h, span, plotWidth) {
    // Semantic block color
    let fillColor = "#10b981"; // calc (green)
    let strokeColor = "#059669";
    
    if (b.block_type === "scatter") {
      fillColor = "#38bdf8"; // cyan / blue
      strokeColor = "#0284c7";
    } else if (b.block_type === "gather") {
      fillColor = "#2563eb"; // deep blue
      strokeColor = "#1d4ed8";
    } else if (b.block_type === "all_reduce") {
      fillColor = "#a855f7"; // purple
      strokeColor = "#7e22ce";
    } else if (b.block_type === "stall") {
      fillColor = "#ef4444"; // red
      strokeColor = "#b91c1c";
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
      ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
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

      ctx.fillStyle = (b.block_type === "calc" || b.block_type === "scatter") ? "#042f2e" : "#ffffff";
      ctx.font = "bold 10px JetBrains Mono, monospace";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";

      let label = b.title || "";
      if (b.layer !== undefined && b.layer >= 0) {
        label = `L${b.layer} | ${label}`;
      }

      if (h >= 24 && w >= 60) {
        // Two lines
        ctx.fillText(label, x + 4, y + h / 2 - 5);
        ctx.font = "9px JetBrains Mono, monospace";
        ctx.fillText(formatTimeNs(b.duration_ns), x + 4, y + h / 2 + 6);
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
        <span class="tooltip-gpu">GPU ${pkt.src} ➔ GPU ${pkt.dst}</span>
      </div>
      <div class="tooltip-body">
        <div class="tooltip-row"><span>Operación / Tipo:</span> <strong>${pkt.op_type || 'Colectiva MoE'}</strong></div>
        <div class="tooltip-row"><span>Flits Totales:</span> <strong>${pkt.flits} flits</strong></div>
        <hr class="tooltip-divider">
        <div class="tooltip-row"><span style="color:#e67e22;">■ Retardo en Cola:</span> <strong>${pkt.queue_delay_cycles.toLocaleString()} c (${formatTimeNs(queueNs)})</strong></div>
        <div class="tooltip-row"><span style="color:#38bdf8;">■ Vuelo NoC (Travesía):</span> <strong>${pkt.flight_cycles.toLocaleString()} c (${formatTimeNs(flightNs)})</strong></div>
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

    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, width, height);

    if (!this.packetsData || !this.packetsData.packets || this.packetsData.packets.length === 0) {
      ctx.fillStyle = "#64748b";
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
          
          let bandColor = "rgba(56, 189, 248, 0.05)";
          if (phase.op_type === "gather") bandColor = "rgba(37, 99, 235, 0.05)";
          else if (phase.op_type === "all_reduce") bandColor = "rgba(168, 85, 247, 0.05)";

          ctx.fillStyle = bandColor;
          ctx.fillRect(x1, this.headerHeight, Math.max(1, x2 - x1), plotHeight);
        }
      });
    }

    // 2. Dual Axes (Top: ns, Bottom: BookSim2 cycles)
    this.drawDualAxes(ctx, width, height, plotWidth, startCycle, endCycle, cycleSpan, clkNs);

    // 3. Render Packet Gantt bars
    const rowHeight = plotHeight / packets.length;

    packets.forEach((p, idx) => {
      const y = this.headerHeight + idx * rowHeight;
      const barH = Math.max(2, rowHeight - 2);

      // Alternating row background
      if (idx % 2 === 0) {
        ctx.fillStyle = "rgba(255, 255, 255, 0.012)";
        ctx.fillRect(0, y, width, rowHeight);
      }

      // Left label: PID and nodes
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px JetBrains Mono, monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`#${p.pid} G${p.src}➔G${p.dst}`, this.marginLeft - 8, y + rowHeight / 2);

      // Segment 1: Queueing Delay (Orange)
      const xCreate = this.marginLeft + ((p.creation_cycle - startCycle) / cycleSpan) * plotWidth;
      const xInject = this.marginLeft + ((p.inject_cycle - startCycle) / cycleSpan) * plotWidth;
      const queueW = Math.max(1, xInject - xCreate);

      ctx.fillStyle = "#e67e22";
      ctx.fillRect(xCreate, y + 1, queueW, barH);

      // Segment 2: NoC Flight Time (Blue)
      const xReceive = this.marginLeft + ((p.receive_cycle - startCycle) / cycleSpan) * plotWidth;
      const flightW = Math.max(1, xReceive - xInject);

      ctx.fillStyle = "#0284c7";
      ctx.fillRect(xInject, y + 1, flightW, barH);
    });
  }

  drawDualAxes(ctx, width, height, plotWidth, startCycle, endCycle, cycleSpan, clkNs) {
    // Top Header Box (Nanoseconds)
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, width, this.headerHeight);
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, this.headerHeight);
    ctx.lineTo(width, this.headerHeight);
    ctx.stroke();

    // Bottom Footer Box (BookSim2 Cycles)
    const footerY = height - this.footerHeight;
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, footerY, width, this.footerHeight);
    ctx.beginPath();
    ctx.moveTo(0, footerY);
    ctx.lineTo(width, footerY);
    ctx.stroke();

    // Axis titles
    ctx.fillStyle = "#38bdf8";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText("Eje Superior: Tiempo Global (ns)", 10, this.headerHeight / 2);

    ctx.fillStyle = "#f59e0b";
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
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px JetBrains Mono, monospace";
      ctx.fillText(formatTimeNs(c * clkNs), x, this.headerHeight - 8);

      // Bottom Tick (cycles)
      ctx.fillText(`${Math.round(c).toLocaleString()} c`, x, footerY + 18);

      // Vertical guide line
      ctx.strokeStyle = "rgba(51, 65, 85, 0.25)";
      ctx.beginPath();
      ctx.moveTo(x, this.headerHeight);
      ctx.lineTo(x, footerY);
      ctx.stroke();
    }
  }
}

/* ==========================================================================
   3. HybridPacketCanvas (Panel Inferior Sincronizado en Nanosegundos)
   ========================================================================== */
class HybridPacketCanvas {
  constructor(canvasEl, tooltipEl, onHoverPacket) {
    this.canvas = canvasEl;
    this.tooltip = tooltipEl;
    this.onHoverPacket = onHoverPacket;

    this.packetsData = null; // { packets, total_in_window, returned, truncated, start_ns, end_ns }
    this.viewStartNs = 0;
    this.viewEndNs = 20000;
    this.minTimeNs = 0;
    this.maxTimeNs = 20000;

    this.marginLeft = 85;
    this.marginRight = 20;
    this.headerHeight = 24;
    this.footerHeight = 8;

    this.crosshairX = null;
    this.crosshairNs = null;
  }

  loadData(packetsResponse, viewStartNs, viewEndNs) {
    if (Array.isArray(packetsResponse)) {
      this.packetsData = { packets: packetsResponse };
    } else {
      this.packetsData = packetsResponse || { packets: [] };
    }
    if (viewStartNs !== undefined) this.viewStartNs = viewStartNs;
    if (viewEndNs !== undefined) this.viewEndNs = viewEndNs;
    this.render();
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

  render() {
    if (!this.canvas) return;
    const { width, height, ctx } = setupHiDPICanvas(this.canvas);
    this.canvas.style.cursor = "crosshair";

    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, width, height);

    const plotWidth = width - this.marginLeft - this.marginRight;
    const plotHeight = height - this.headerHeight - this.footerHeight;
    const span = this.viewEndNs - this.viewStartNs;

    if (span <= 0) return;

    // Header axis line
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, this.headerHeight);
    ctx.lineTo(width, this.headerHeight);
    ctx.stroke();

    if (!this.packetsData || !this.packetsData.packets || this.packetsData.packets.length === 0) {
      ctx.fillStyle = "#64748b";
      ctx.font = "12px JetBrains Mono, monospace";
      ctx.textAlign = "center";
      ctx.fillText("No hay paquetes en tránsito dentro de esta ventana de tiempo.", width / 2, height / 2 + 5);
      this.drawCrosshairLine(ctx, height, plotWidth);
      return;
    }

    const packets = this.packetsData.packets;
    const rowHeight = Math.max(5, Math.min(22, plotHeight / packets.length));
    const barH = Math.max(3, rowHeight - 2);

    for (let i = 0; i < packets.length; i++) {
      const p = packets[i];
      const y = this.headerHeight + i * rowHeight;

      if (i % 2 === 0) {
        ctx.fillStyle = "rgba(255, 255, 255, 0.015)";
        ctx.fillRect(this.marginLeft, y, plotWidth, rowHeight);
      }

      // Left label
      if (rowHeight >= 10) {
        ctx.fillStyle = "#94a3b8";
        ctx.font = "9px JetBrains Mono, monospace";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        ctx.fillText(`#${p.pid} G${p.src}➔G${p.dst}`, this.marginLeft - 6, y + rowHeight / 2);
      }

      // Segment 1: Queueing delay [pkt_start_ns, pkt_inject_ns] in orange
      const xStart = this.marginLeft + ((p.pkt_start_ns - this.viewStartNs) / span) * plotWidth;
      const xInject = this.marginLeft + ((p.pkt_inject_ns - this.viewStartNs) / span) * plotWidth;
      const queueW = Math.max(1, xInject - xStart);

      ctx.fillStyle = "#e67e22"; // orange
      ctx.fillRect(xStart, y + 1, queueW, barH);

      // Segment 2: NoC flight time [pkt_inject_ns, pkt_end_ns] in blue
      const xEnd = this.marginLeft + ((p.pkt_end_ns - this.viewStartNs) / span) * plotWidth;
      const flightW = Math.max(1, xEnd - xInject);

      ctx.fillStyle = "#0284c7"; // blue
      ctx.fillRect(xInject, y + 1, flightW, barH);
    }

    this.drawCrosshairLine(ctx, height, plotWidth);
  }

  drawCrosshairLine(ctx, height, plotWidth) {
    if (this.crosshairX !== null && this.crosshairX !== undefined &&
        this.crosshairX >= this.marginLeft && this.crosshairX <= this.marginLeft + plotWidth) {
      ctx.save();
      ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(this.crosshairX, this.headerHeight);
      ctx.lineTo(this.crosshairX, height - this.footerHeight);
      ctx.stroke();

      if (this.crosshairNs !== null) {
        ctx.fillStyle = "#38bdf8";
        ctx.fillRect(this.crosshairX - 32, height - this.footerHeight - 16, 64, 16);
        ctx.fillStyle = "#000";
        ctx.font = "bold 9px JetBrains Mono, monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(formatTimeNs(this.crosshairNs), this.crosshairX, height - this.footerHeight - 8);
      }
      ctx.restore();
    }
  }

  getPacketAt(x, y) {
    if (!this.packetsData || !this.packetsData.packets || this.packetsData.packets.length === 0) return null;
    const rect = this.canvas.getBoundingClientRect();
    const plotHeight = rect.height - this.headerHeight - this.footerHeight;
    const packets = this.packetsData.packets;
    const rowHeight = plotHeight / packets.length;

    const rowIdx = Math.floor((y - this.headerHeight) / rowHeight);
    if (rowIdx >= 0 && rowIdx < packets.length) {
      return packets[rowIdx];
    }
    return null;
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
      this.tooltipEl,
      (pkt) => {}
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
          const pkt = this.packetCanvas.getPacketAt(x, y);
          if (pkt) {
            this.showPacketTooltip(pkt, e.clientX, e.clientY);
          } else {
            this.hideTooltip();
          }
        }
      } else {
        this.chronoCanvas.clearCrosshair();
        this.packetCanvas.clearCrosshair();
        this.hideTooltip();
      }
    };

    const handleLeave = () => {
      this.chronoCanvas.clearCrosshair();
      this.packetCanvas.clearCrosshair();
      this.hideTooltip();
    };

    this.chronoCanvasEl.addEventListener("mousemove", (e) => handleMove(e, this.chronoCanvasEl));
    this.packetsCanvasEl.addEventListener("mousemove", (e) => handleMove(e, this.packetsCanvasEl));

    this.chronoCanvasEl.addEventListener("mouseleave", handleLeave);
    this.packetsCanvasEl.addEventListener("mouseleave", handleLeave);

    const handleWheel = (e, canvasTarget) => {
      e.preventDefault();
      const rect = canvasTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const plotWidth = rect.width - this.chronoCanvas.marginLeft - this.chronoCanvas.marginRight;
      let ratio = 0.5;
      if (x >= this.chronoCanvas.marginLeft && x <= rect.width - this.chronoCanvas.marginRight) {
        ratio = (x - this.chronoCanvas.marginLeft) / plotWidth;
      }
      const factor = e.deltaY > 0 ? 1.15 : 0.85;
      this.zoom(factor, ratio);
    };

    this.chronoCanvasEl.addEventListener("wheel", (e) => handleWheel(e, this.chronoCanvasEl), { passive: false });
    this.packetsCanvasEl.addEventListener("wheel", (e) => handleWheel(e, this.packetsCanvasEl), { passive: false });

    const handleMouseDown = (e, canvasTarget) => {
      const rect = canvasTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (x < this.chronoCanvas.marginLeft) return;

      this.isDragging = true;
      this.dragStartX = e.clientX;
      this.dragStartViewStart = this.viewStartNs;
      this.dragStartViewEnd = this.viewEndNs;
      this.chronoCanvasEl.style.cursor = "grabbing";
      this.packetsCanvasEl.style.cursor = "grabbing";
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
        this.packetsCanvasEl.style.cursor = "crosshair";
      }
    };

    this.chronoCanvasEl.addEventListener("mousedown", (e) => handleMouseDown(e, this.chronoCanvasEl));
    this.packetsCanvasEl.addEventListener("mousedown", (e) => handleMouseDown(e, this.packetsCanvasEl));
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

    const spanUs = (newEnd - newStart) / 1000;
    if (this.windowInfoEl) {
      this.windowInfoEl.textContent = `Ventana: ${(newStart / 1000).toFixed(2)} µs ➔ ${(newEnd / 1000).toFixed(2)} µs (${spanUs.toFixed(2)} µs)`;
    }
    if (this.scrubberPosEl) {
      this.scrubberPosEl.textContent = `${(newStart / 1000).toFixed(2)} µs`;
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

  triggerFetchPackets() {
    clearTimeout(this.fetchDebounceTimer);
    this.fetchDebounceTimer = setTimeout(async () => {
      if (this.fetchPacketsWindowFn) {
        const data = await this.fetchPacketsWindowFn(this.viewStartNs, this.viewEndNs);
        if (data) {
          this.packetCanvas.loadData(data, this.viewStartNs, this.viewEndNs);
          if (this.packetBadgeEl) {
            const count = data.total_in_window || 0;
            const truncText = data.truncated ? ` (${data.returned} mostrados, muestreado)` : "";
            this.packetBadgeEl.textContent = `${count} paquetes en ventana${truncText}`;
          }
        }
      }
    }, 60);
  }

  showPacketTooltip(pkt, clientX, clientY) {
    if (!this.tooltipEl) return;
    this.tooltipEl.innerHTML = `
      <div class="tooltip-header">
        <span class="badge badge-scatter">PID #${pkt.pid}</span>
        <span class="tooltip-gpu">GPU ${pkt.src} ➔ GPU ${pkt.dst}</span>
      </div>
      <div class="tooltip-body">
        <div class="tooltip-row"><span>Operación:</span> <strong>${pkt.op_type} Nº${pkt.op_idx || 1}</strong></div>
        <div class="tooltip-row"><span>Flits:</span> <strong>${pkt.flits} flits</strong></div>
        <hr class="tooltip-divider">
        <div class="tooltip-row"><span style="color:#e67e22;">■ Retardo en Cola:</span> <strong>${pkt.queue_delay_cycles} c</strong></div>
        <div class="tooltip-row"><span style="color:#38bdf8;">■ Travesía NoC:</span> <strong>${pkt.flight_cycles} c</strong></div>
        <div class="tooltip-row"><span>Latencia Paquete:</span> <strong class="highlight-val">${pkt.total_latency_cycles} c</strong></div>
        <hr class="tooltip-divider">
        <div class="tooltip-row"><span>Inicio (Creación):</span> <code>${formatTimeNs(pkt.pkt_start_ns)}</code></div>
        <div class="tooltip-row"><span>Inyección en NoC:</span> <code>${formatTimeNs(pkt.pkt_inject_ns)}</code></div>
        <div class="tooltip-row"><span>Recepción Destino:</span> <code>${formatTimeNs(pkt.pkt_end_ns)}</code></div>
      </div>
    `;

    this.tooltipEl.classList.remove("hidden");
    const tipRect = this.tooltipEl.getBoundingClientRect();
    let left = clientX + 15;
    let top = clientY + 15;

    if (left + tipRect.width > window.innerWidth - 10) left = clientX - tipRect.width - 15;
    if (top + tipRect.height > window.innerHeight - 10) top = window.innerHeight - tipRect.height - 10;

    this.tooltipEl.style.left = `${Math.max(10, left)}px`;
    this.tooltipEl.style.top = `${Math.max(10, top)}px`;
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

