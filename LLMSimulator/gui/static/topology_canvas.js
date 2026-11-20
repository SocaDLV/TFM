/**
 * Topology and NoC Heatmap Visualizer for LLM-NoC Co-Simulation Workbench.
 * Renders interactive vector network graphs for 1D Torus/Ring, 2D Mesh/Torus,
 * and 3D Mesh/Torus topologies. Superimposes traffic heatmaps, in-cast hotspots,
 * physical link latencies, and weighted directional flows (Src -> Dst).
 *
 * Phase 4.5: Dynamic thermal gradient on physical links and flows, with
 * geometric hit-testing for interactive hover tooltips over connections.
 */

class TopologyCanvas {
  constructor(canvasId, tooltipId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.tooltip = document.getElementById(tooltipId);

    this.data = null;
    this.activeMetric = "rx_share"; // 'rx_share' | 'tx_share' | 'rx_pkts' | 'tx_pkts' | 'queue_delay' | 'latency' | 'stall_time'
    this.showFlows = true;
    this.showLabels = true;
    this.selectedNodeId = null;
    this.hoveredNodeId = null;
    this.hoveredEdge = null;
    this.renderedEdges = [];

    this.nodePositions = {};
    this.onNodeSelected = null;

    this.resizeObserver = new ResizeObserver(() => this.resizeAndRender());
    this.resizeObserver.observe(this.canvas.parentElement);

    this.canvas.addEventListener("mousemove", (e) => this.handleMouseMove(e));
    this.canvas.addEventListener("mouseleave", () => this.handleMouseLeave());
    this.canvas.addEventListener("click", (e) => this.handleClick(e));
  }

  setData(topoData) {
    this.data = topoData;
    this.selectedNodeId = null;
    this.hoveredNodeId = null;
    this.hoveredEdge = null;
    this.renderedEdges = [];
    this.resizeAndRender();
  }

  setMetric(metricName) {
    this.activeMetric = metricName;
    this.render();
  }

  setShowFlows(val) {
    this.showFlows = Boolean(val);
    this.render();
  }

  setShowLabels(val) {
    this.showLabels = Boolean(val);
    this.render();
  }

  selectNode(nodeId) {
    this.selectedNodeId = nodeId;
    this.render();
    if (this.onNodeSelected && this.data && this.data.nodes) {
      const node = this.data.nodes.find(n => n.id === nodeId);
      this.onNodeSelected(node);
    }
  }

  resizeAndRender() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parent = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const rect = parent.getBoundingClientRect();
    const w = Math.max(300, rect.width);
    const h = Math.max(480, rect.height || 540);

    this.canvas.width = w * dpr;
    this.canvas.height = h * dpr;
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;

    this.ctx.resetTransform();
    this.ctx.scale(dpr, dpr);
    this.width = w;
    this.height = h;

    this.computeLayout();
    this.render();
  }

  computeLayout() {
    if (!this.data || !this.data.nodes || this.data.nodes.length === 0) {
      this.nodePositions = {};
      return;
    }

    const nodes = this.data.nodes;
    const n = nodes.length;
    const topo = (this.data.topology || "torus").toLowerCase();
    const dimsStr = String(this.data.net_dims || `${n}`);
    const w = this.width || 600;
    const h = this.height || 500;
    const cx = w / 2;
    const cy = h / 2;

    this.nodePositions = {};
    const nodeRadius = n <= 8 ? 26 : 21;

    // 1. Detect 3D Mesh / Torus (e.g. 2 2 2)
    const dimNums = dimsStr.match(/\d+/g) || [];
    if (dimNums.length === 3 && parseInt(dimNums[0]) * parseInt(dimNums[1]) * parseInt(dimNums[2]) === n) {
      const kx = parseInt(dimNums[0]);
      const ky = parseInt(dimNums[1]);
      const kz = parseInt(dimNums[2]);

      const layerSpacing = Math.min(w * 0.45, 240);
      const stepX = Math.min(120, (w * 0.4) / Math.max(1, kx - 1));
      const stepY = Math.min(100, (h * 0.6) / Math.max(1, ky - 1));

      for (let z = 0; z < kz; z++) {
        const layerOriginX = cx - (kz - 1) * layerSpacing / 2 + z * layerSpacing - (kx - 1) * stepX / 2;
        const layerOriginY = cy - (ky - 1) * stepY / 2;
        for (let y = 0; y < ky; y++) {
          for (let x = 0; x < kx; x++) {
            const id = z * (kx * ky) + y * kx + x;
            if (id < n) {
              this.nodePositions[id] = {
                x: layerOriginX + x * stepX,
                y: layerOriginY + y * stepY,
                r: nodeRadius,
                layerZ: z
              };
            }
          }
        }
      }
      return;
    }

    // 2. Detect 2D Mesh / Torus (e.g. "4 2", "2 2", "4 4")
    let kx = n, ky = 1;
    const m2d = dimsStr.match(/(\d+)[x\s](\d+)/);
    if (m2d) {
      kx = parseInt(m2d[1]);
      ky = parseInt(m2d[2]);
    } else if (topo === "mesh" && n === 8) {
      kx = 4; ky = 2;
    } else if (topo === "mesh" && n === 4) {
      kx = 2; ky = 2;
    }

    if (ky > 1) {
      const padX = Math.min(90, w * 0.12);
      const padY = Math.min(80, h * 0.14);
      const availW = w - padX * 2;
      const availH = h - padY * 2;
      const stepX = availW / Math.max(1, kx - 1);
      const stepY = availH / Math.max(1, ky - 1);

      for (let y = 0; y < ky; y++) {
        for (let x = 0; x < kx; x++) {
          const id = y * kx + x;
          if (id < n) {
            this.nodePositions[id] = {
              x: padX + x * stepX,
              y: padY + y * stepY,
              r: nodeRadius,
              gridX: x,
              gridY: y
            };
          }
        }
      }
      return;
    }

    // 3. 1D Torus or Ring Layout (Circular Ring)
    const ringRadius = Math.min(cx, cy) - Math.max(50, nodeRadius + 35);
    for (let i = 0; i < n; i++) {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      this.nodePositions[i] = {
        x: cx + ringRadius * Math.cos(angle),
        y: cy + ringRadius * Math.sin(angle),
        r: nodeRadius,
        angle: angle
      };
    }
  }

  getNodeValue(node) {
    if (!node) return 0;
    switch (this.activeMetric) {
      case "rx_share":
        return node.rx_share_pct || 0;
      case "tx_share":
        return node.tx_share_pct || 0;
      case "rx_pkts":
        return node.rx_packets || 0;
      case "tx_pkts":
        return node.tx_packets || 0;
      case "queue_delay":
        return node.avg_queueing_delay || 0;
      case "latency":
        return node.avg_total_latency || 0;
      case "stall_time":
        return node.stall_us || 0;
      default:
        return node.rx_share_pct || 0;
    }
  }

  getLinkValue(link) {
    if (!link) return 0;
    switch (this.activeMetric) {
      case "rx_share":
      case "tx_share":
        return link.share_pct || 0;
      case "rx_pkts":
      case "tx_pkts":
        return link.packets || 0;
      case "queue_delay":
        return link.avg_queueing_delay || 0;
      case "latency":
        return link.avg_network_latency || 0;
      case "stall_time":
        return link.avg_stall_us || 0;
      default:
        return link.packets || 0;
    }
  }

  getFlowValue(flow) {
    if (!flow) return 0;
    switch (this.activeMetric) {
      case "rx_share":
      case "tx_share":
        return flow.share_pct || 0;
      case "rx_pkts":
      case "tx_pkts":
        return flow.packets || 0;
      case "queue_delay":
        return flow.avg_queueing_delay !== undefined ? flow.avg_queueing_delay : (flow.avg_queue || 0);
      case "latency":
        return flow.avg_network_latency !== undefined ? flow.avg_network_latency : (flow.avg_latency || 0);
      case "stall_time":
        return flow.packets || 0;
      default:
        return flow.packets || 0;
    }
  }

  getMetricFormat(val) {
    switch (this.activeMetric) {
      case "rx_share":
      case "tx_share":
        return `${val.toFixed(1)}%`;
      case "rx_pkts":
      case "tx_pkts":
        return val >= 10000 ? `${(val / 1000).toFixed(1)}k` : `${val}`;
      case "queue_delay":
        return `${val.toFixed(0)}c`;
      case "latency":
        return `${val.toFixed(0)}c`;
      case "stall_time":
        return val >= 1000 ? `${(val / 1000).toFixed(2)}ms` : `${val.toFixed(1)}µs`;
      default:
        return `${val.toFixed(1)}%`;
    }
  }

  getMetricLabel() {
    switch (this.activeMetric) {
      case "rx_share":
        return "Carga Recibida (RX %)";
      case "tx_share":
        return "Carga Emitida (TX %)";
      case "rx_pkts":
        return "Paquetes Recibidos (RX)";
      case "tx_pkts":
        return "Paquetes Emitidos (TX)";
      case "queue_delay":
        return "Retardo en Cola NIC (ciclos)";
      case "latency":
        return "Latencia de Red / Contención NoC (ciclos)";
      case "stall_time":
        return "Tiempo de Bloqueo (Stall)";
      default:
        return "Carga Recibida";
    }
  }

  getHeatColor(ratio) {
    const t = Math.max(0, Math.min(1, isNaN(ratio) ? 0 : ratio));
    let r, g, b;
    if (t < 0.33) {
      const s = t / 0.33;
      r = Math.round(14 + s * (16 - 14));
      g = Math.round(116 + s * (185 - 116));
      b = Math.round(144 + s * (129 - 144));
    } else if (t < 0.66) {
      const s = (t - 0.33) / 0.33;
      r = Math.round(16 + s * (245 - 16));
      g = Math.round(185 + s * (158 - 185));
      b = Math.round(129 + s * (11 - 129));
    } else {
      const s = (t - 0.66) / 0.34;
      r = Math.round(245 + s * (239 - 245));
      g = Math.round(158 + s * (68 - 158));
      b = Math.round(11 + s * (68 - 11));
    }

    return {
      rgb: `rgb(${r}, ${g}, ${b})`,
      rgba: (a) => `rgba(${r}, ${g}, ${b}, ${a})`,
      r, g, b,
      ratio: t
    };
  }

  getNodeColor(val, minVal, maxVal) {
    if (maxVal <= minVal || isNaN(val)) {
      return { fill: "#1e293b", stroke: "#0284c7", text: "#e2e8f0", ratio: 0 };
    }

    const t = Math.max(0, Math.min(1, (val - minVal) / (maxVal - minVal)));
    const heat = this.getHeatColor(t);

    return {
      fill: heat.rgb,
      stroke: t > 0.66 ? "#fecaca" : (t > 0.33 ? "#fef08a" : "#bae6fd"),
      text: (t > 0.4 && t < 0.7) ? "#0f172a" : "#ffffff",
      ratio: t
    };
  }

  // Geometry Distance Calculations for Hit-Testing
  pointToSegmentDistance(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.hypot(px - x1, py - y1);
    const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lenSq));
    const projX = x1 + t * dx;
    const projY = y1 + t * dy;
    return Math.hypot(px - projX, py - projY);
  }

  pointToQuadraticBezierDistance(px, py, x1, y1, cx, cy, x2, y2, samples = 24) {
    let minDist = Infinity;
    let prevX = x1;
    let prevY = y1;
    for (let i = 1; i <= samples; i++) {
      const t = i / samples;
      const it = 1 - t;
      const curX = it * it * x1 + 2 * it * t * cx + t * t * x2;
      const curY = it * it * y1 + 2 * it * t * cy + t * t * y2;
      const d = this.pointToSegmentDistance(px, py, prevX, prevY, curX, curY);
      if (d < minDist) minDist = d;
      prevX = curX;
      prevY = curY;
    }
    return minDist;
  }

  render() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    // Reset rendered edge bounding cache
    this.renderedEdges = [];

    // Clear background
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, w, h);

    if (!this.data || !this.data.nodes || this.data.nodes.length === 0) {
      ctx.fillStyle = "#64748b";
      ctx.font = "14px JetBrains Mono, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("Selecciona o ejecuta una simulación para inspeccionar su topología NoC.", w / 2, h / 2);
      return;
    }

    const nodes = this.data.nodes;
    const links = this.data.links || [];
    const flows = this.data.flows || [];

    // Compute metric min and max
    let minVal = Infinity;
    let maxVal = -Infinity;
    nodes.forEach(n => {
      const v = this.getNodeValue(n);
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    });
    if (minVal === Infinity) minVal = 0;
    if (maxVal === -Infinity || maxVal <= minVal) maxVal = minVal + 1;

    // Render Layers
    this.renderLegend(minVal, maxVal);
    this.renderPhysicalLinks(links);
    if (this.showFlows && flows.length > 0) {
      this.renderTrafficFlows(flows);
    }
    this.renderNodes(nodes, minVal, maxVal);
  }

  renderLegend(minVal, maxVal) {
    const ctx = this.ctx;
    const x = 20;
    const y = 16;
    const barW = 160;
    const barH = 10;

    const grad = ctx.createLinearGradient(x, y, x + barW, y);
    grad.addColorStop(0.0, "rgb(14, 116, 144)");
    grad.addColorStop(0.35, "rgb(16, 185, 129)");
    grad.addColorStop(0.65, "rgb(245, 158, 11)");
    grad.addColorStop(1.0, "rgb(239, 68, 68)");

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(x, y, barW, barH, 4);
    ctx.fill();

    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.fillText(this.getMetricLabel(), x, y - 4);

    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText(this.getMetricFormat(minVal), x, y + barH + 3);

    ctx.textAlign = "right";
    ctx.fillText(this.getMetricFormat(maxVal), x + barW, y + barH + 3);
  }

  renderPhysicalLinks(links) {
    const ctx = this.ctx;
    const pos = this.nodePositions;
    const topo = (this.data.topology || "torus").toLowerCase();
    const hasData = Boolean(this.data && this.data.has_packet_data && !this.data.preview_mode);

    // Compute max link value for normalization
    let maxLinkVal = 0;
    if (hasData) {
      links.forEach(l => {
        const v = this.getLinkValue(l);
        if (v > maxLinkVal) maxLinkVal = v;
      });
      if (maxLinkVal <= 0) maxLinkVal = 1;
    }

    links.forEach(l => {
      const p1 = pos[l.src];
      const p2 = pos[l.dst];
      if (!p1 || !p2) return;

      const isWrap = l.type === "wraparound";
      const isHovered = Boolean(
        this.hoveredEdge &&
        this.hoveredEdge.type === "link" &&
        ((this.hoveredEdge.data.src === l.src && this.hoveredEdge.data.dst === l.dst) ||
         (this.hoveredEdge.data.src === l.dst && this.hoveredEdge.data.dst === l.src))
      );

      let strokeColor = "#334155";
      let lineWidth = 2.0;
      let ratio = 0;

      if (hasData) {
        const val = this.getLinkValue(l);
        ratio = Math.max(0, Math.min(1, val / maxLinkVal));
        const heat = this.getHeatColor(ratio);
        strokeColor = heat.rgb;
        lineWidth = 2.0 + ratio * 5.5; // 2.0px to 7.5px
      } else {
        strokeColor = isWrap ? "#a855f7" : "#38bdf8";
        lineWidth = isWrap ? 2.4 : 2.0;
      }

      ctx.save();

      // Saturation glow or Hover highlight
      if (isHovered) {
        ctx.strokeStyle = "#f8fafc";
        ctx.lineWidth = lineWidth + 2.5;
        ctx.shadowColor = "rgba(248, 250, 252, 0.95)";
        ctx.shadowBlur = 12;
      } else if (hasData && ratio > 0.70) {
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.shadowColor = "rgba(239, 68, 68, 0.65)";
        ctx.shadowBlur = 10;
      } else {
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.shadowBlur = 0;
      }

      if (isWrap) {
        // Curved wrap-around link (Dateline 2 cycles)
        if (!isHovered) {
          ctx.setLineDash([5, 4]);
        }

        ctx.beginPath();
        let cpX, cpY;
        if (topo === "torus" && (this.data.net_dims === "8" || !String(this.data.net_dims).includes(" "))) {
          // Arc bulging outward from center
          const cx = this.width / 2;
          const cy = this.height / 2;
          const midX = (p1.x + p2.x) / 2;
          const midY = (p1.y + p2.y) / 2;
          const dx = midX - cx;
          const dy = midY - cy;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          cpX = midX + (dx / dist) * 70;
          cpY = midY + (dy / dist) * 70;
        } else {
          // Curved 2D boundary wrap-around
          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const nx = -dy / dist;
          const ny = dx / dist;
          const offset = 42;
          cpX = (p1.x + p2.x) / 2 + nx * offset;
          cpY = (p1.y + p2.y) / 2 + ny * offset;
        }

        ctx.moveTo(p1.x, p1.y);
        ctx.quadraticCurveTo(cpX, cpY, p2.x, p2.y);
        ctx.stroke();

        // Record rendered edge for hit-testing
        this.renderedEdges.push({
          type: "link",
          isCurve: true,
          x1: p1.x, y1: p1.y,
          cx: cpX, cy: cpY,
          x2: p2.x, y2: p2.y,
          lineWidth: lineWidth,
          data: l
        });

        if (this.showLabels) {
          ctx.fillStyle = isHovered ? "#ffffff" : (hasData ? strokeColor : "#c084fc");
          ctx.font = "bold 9px JetBrains Mono, monospace";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("2c (Wrap)", cpX, cpY);
        }
      } else {
        // Direct physical neighbor link (1 cycle)
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        // Record rendered edge for hit-testing
        this.renderedEdges.push({
          type: "link",
          isCurve: false,
          x1: p1.x, y1: p1.y,
          x2: p2.x, y2: p2.y,
          lineWidth: lineWidth,
          data: l
        });

        if (this.showLabels && links.length <= 16) {
          const mx = (p1.x + p2.x) / 2;
          const my = (p1.y + p2.y) / 2;
          ctx.fillStyle = isHovered ? "#ffffff" : (hasData ? strokeColor : "#64748b");
          ctx.font = "8px JetBrains Mono, monospace";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("1c", mx, my);
        }
      }
      ctx.restore();
    });
  }

  renderTrafficFlows(flows) {
    const ctx = this.ctx;
    const pos = this.nodePositions;
    let maxFlowVal = 0;
    flows.forEach(f => {
      const v = this.getFlowValue(f);
      if (v > maxFlowVal) maxFlowVal = v;
    });
    if (maxFlowVal <= 0) maxFlowVal = 1;

    // Filter flows if a node is focused/hovered
    const focusId = this.hoveredNodeId !== null ? this.hoveredNodeId : this.selectedNodeId;

    flows.forEach(f => {
      const p1 = pos[f.src];
      const p2 = pos[f.dst];
      if (!p1 || !p2) return;

      const isConnected = focusId === null || (f.src === focusId || f.dst === focusId);
      const isOutgoing = focusId !== null && f.src === focusId;
      const isIncoming = focusId !== null && f.dst === focusId;
      const isHovered = Boolean(
        this.hoveredEdge &&
        this.hoveredEdge.type === "flow" &&
        this.hoveredEdge.data.src === f.src &&
        this.hoveredEdge.data.dst === f.dst
      );

      const val = this.getFlowValue(f);
      const ratio = Math.max(0, Math.min(1, val / maxFlowVal));
      const heat = this.getHeatColor(ratio);

      const baseAlpha = 0.25 + ratio * 0.65;
      let alpha = isConnected ? baseAlpha : 0.05;
      let lineW = Math.max(1.4, 1.4 + ratio * 4.6);

      let strokeColor = heat.rgb;
      if (focusId !== null) {
        if (isOutgoing) strokeColor = "#fbbf24";
        if (isIncoming) strokeColor = "#f43f5e";
      }

      ctx.save();

      if (isHovered) {
        strokeColor = "#f8fafc";
        alpha = 1.0;
        lineW += 2.5;
        ctx.shadowColor = "rgba(248, 250, 252, 0.95)";
        ctx.shadowBlur = 12;
      } else {
        ctx.shadowBlur = 0;
      }

      ctx.strokeStyle = strokeColor;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = lineW;

      // Slight perpendicular curve so bidirectional flows don't collide
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 1) { ctx.restore(); return; }

      const nx = -dy / dist;
      const ny = dx / dist;
      const curveAmount = Math.min(28, dist * 0.12);
      const midX = (p1.x + p2.x) / 2 + nx * curveAmount;
      const midY = (p1.y + p2.y) / 2 + ny * curveAmount;

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.quadraticCurveTo(midX, midY, p2.x, p2.y);
      ctx.stroke();

      // Record rendered flow for hit-testing
      if (isConnected) {
        this.renderedEdges.push({
          type: "flow",
          isCurve: true,
          x1: p1.x, y1: p1.y,
          cx: midX, cy: midY,
          x2: p2.x, y2: p2.y,
          lineWidth: lineW,
          data: f
        });
      }

      // Render arrowhead along the curve
      if (isConnected && (ratio > 0.08 || isHovered)) {
        const arrowT = 0.65;
        const ax = (1 - arrowT) * (1 - arrowT) * p1.x + 2 * (1 - arrowT) * arrowT * midX + arrowT * arrowT * p2.x;
        const ay = (1 - arrowT) * (1 - arrowT) * p1.y + 2 * (1 - arrowT) * arrowT * midY + arrowT * arrowT * p2.y;
        const angle = Math.atan2(p2.y - midY, p2.x - midX);

        ctx.fillStyle = strokeColor;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - 9 * Math.cos(angle - Math.PI / 6), ay - 9 * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(ax - 9 * Math.cos(angle + Math.PI / 6), ay - 9 * Math.sin(angle + Math.PI / 6));
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
    });
  }

  renderNodes(nodes, minVal, maxVal) {
    const ctx = this.ctx;
    const pos = this.nodePositions;

    nodes.forEach(n => {
      const p = pos[n.id];
      if (!p) return;

      const val = this.getNodeValue(n);
      const color = this.getNodeColor(val, minVal, maxVal);
      const isSelected = this.selectedNodeId === n.id;
      const isHovered = this.hoveredNodeId === n.id;

      ctx.save();

      // Selection or Hotspot Halo Ring
      if (isSelected || isHovered || color.ratio > 0.75) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r + 6, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? "rgba(56, 189, 248, 0.35)" : (isHovered ? "rgba(255, 255, 255, 0.25)" : "rgba(239, 68, 68, 0.25)");
        ctx.fill();
      }

      // Main Node Circle
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, 2 * Math.PI);
      ctx.fillStyle = color.fill;
      ctx.fill();

      ctx.strokeStyle = isSelected ? "#38bdf8" : (isHovered ? "#ffffff" : color.stroke);
      ctx.lineWidth = isSelected ? 3.0 : (isHovered ? 2.5 : 1.8);
      ctx.stroke();

      // GPU Identifier Text
      ctx.fillStyle = color.text;
      ctx.font = "bold 11px JetBrains Mono, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(`GPU ${n.id}`, p.x, p.y - 4);

      // Active Metric Text
      ctx.fillStyle = color.text;
      ctx.font = "9.5px JetBrains Mono, monospace";
      ctx.fillText(this.getMetricFormat(val), p.x, p.y + 7);

      // Expert Badge Below Node
      if (n.experts) {
        ctx.font = "8px JetBrains Mono, monospace";
        ctx.fillStyle = "#94a3b8";
        let expStr = n.experts;
        if (expStr.length > 14) {
          expStr = expStr.replace(" + Shared", "+S").replace("Micro-Exp", "Exp");
        }
        ctx.fillText(expStr, p.x, p.y + p.r + 11);
      }

      ctx.restore();
    });
  }

  handleMouseMove(e) {
    if (!this.data || !this.data.nodes) return;
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // 1. Prioritize Node Hit-Testing
    let foundNodeId = null;
    for (const n of this.data.nodes) {
      const p = this.nodePositions[n.id];
      if (!p) continue;
      const dx = mx - p.x;
      const dy = my - p.y;
      if (dx * dx + dy * dy <= (p.r + 5) * (p.r + 5)) {
        foundNodeId = n.id;
        break;
      }
    }

    if (foundNodeId !== null) {
      if (this.hoveredNodeId !== foundNodeId || this.hoveredEdge !== null) {
        this.hoveredNodeId = foundNodeId;
        this.hoveredEdge = null;
        this.canvas.style.cursor = "pointer";
        this.render();
      }
      const node = this.data.nodes.find(n => n.id === foundNodeId);
      this.showTooltip(node, e.clientX, e.clientY);
      return;
    }

    // 2. Connection Hit-Testing (Flows and Physical Links)
    let closestEdge = null;
    let minEdgeDist = Infinity;
    const tolerance = 8.0;

    for (const edge of this.renderedEdges) {
      let d = Infinity;
      if (edge.isCurve) {
        d = this.pointToQuadraticBezierDistance(mx, my, edge.x1, edge.y1, edge.cx, edge.cy, edge.x2, edge.y2);
      } else {
        d = this.pointToSegmentDistance(mx, my, edge.x1, edge.y1, edge.x2, edge.y2);
      }

      const hitDist = Math.max(tolerance, (edge.lineWidth || 2.0) / 2 + 5);
      if (d <= hitDist && d < minEdgeDist) {
        minEdgeDist = d;
        closestEdge = edge;
      }
    }

    if (closestEdge !== null) {
      const edgeChanged = !this.hoveredEdge ||
        this.hoveredEdge.type !== closestEdge.type ||
        this.hoveredEdge.data !== closestEdge.data;

      if (edgeChanged || this.hoveredNodeId !== null) {
        this.hoveredNodeId = null;
        this.hoveredEdge = closestEdge;
        this.canvas.style.cursor = "pointer";
        this.render();
      }
      this.showEdgeTooltip(closestEdge, e.clientX, e.clientY);
      return;
    }

    // 3. Neither Node Nor Connection
    if (this.hoveredNodeId !== null || this.hoveredEdge !== null) {
      this.hoveredNodeId = null;
      this.hoveredEdge = null;
      this.canvas.style.cursor = "default";
      this.hideTooltip();
      this.render();
    }
  }

  handleMouseLeave() {
    if (this.hoveredNodeId !== null || this.hoveredEdge !== null) {
      this.hoveredNodeId = null;
      this.hoveredEdge = null;
      this.render();
      this.hideTooltip();
      this.canvas.style.cursor = "default";
    }
  }

  handleClick(e) {
    if (!this.data || !this.data.nodes) return;
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    for (const n of this.data.nodes) {
      const p = this.nodePositions[n.id];
      if (!p) continue;
      const dx = mx - p.x;
      const dy = my - p.y;
      if (dx * dx + dy * dy <= (p.r + 5) * (p.r + 5)) {
        this.selectNode(n.id);
        return;
      }
    }

    // Deselect if clicked outside
    this.selectNode(null);
  }

  showTooltip(node, clientX, clientY) {
    if (!this.tooltip || !node) return;

    this.tooltip.innerHTML = `
      <div class="tooltip-header">
        <span class="badge badge-scatter">Router NoC ${node.id}</span>
        <span class="tooltip-gpu">GPU ${node.id}</span>
      </div>
      <div class="tooltip-body">
        <div class="tooltip-row"><span>Expertos:</span> <strong>${node.experts || '-'}</strong></div>
        <div class="tooltip-row"><span>Carga RX:</span> <strong style="color:#ef4444;">${node.rx_share_pct.toFixed(1)}% (${node.rx_packets.toLocaleString()} pkts)</strong></div>
        <div class="tooltip-row"><span>Carga TX:</span> <strong style="color:#38bdf8;">${node.tx_share_pct.toFixed(1)}% (${node.tx_packets.toLocaleString()} pkts)</strong></div>
        <div class="tooltip-row"><span>Retardo Cola NIC:</span> <strong>${node.avg_queueing_delay.toFixed(1)} ciclos</strong></div>
        <div class="tooltip-row"><span>Latencia Media NoC:</span> <strong>${node.avg_total_latency.toFixed(1)} ciclos</strong></div>
        <div class="tooltip-row"><span>Cómputo GPU:</span> <strong>${node.compute_us.toFixed(1)} µs</strong></div>
        <div class="tooltip-row"><span>Tránsito NoC:</span> <strong>${node.transit_us.toFixed(1)} µs</strong></div>
        <div class="tooltip-row"><span>Stalls BSP:</span> <strong style="color:#f59e0b;">${node.stall_us.toFixed(1)} µs</strong></div>
      </div>
    `;

    this.positionTooltip(clientX, clientY);
  }

  showEdgeTooltip(edge, clientX, clientY) {
    if (!this.tooltip || !edge) return;

    if (edge.type === "link") {
      const l = edge.data;
      const isWrap = l.type === "wraparound";
      const typeText = isWrap ? "Wrap-Around Dateline (2 ciclos)" : "Enlace Vecino (1 ciclo)";
      const totalClusterPkts = this.data.total_packets || 1;
      const sharePct = (l.share_pct !== undefined) ? l.share_pct : ((l.packets || 0) / totalClusterPkts * 100);
      const u = l.src;
      const v = l.dst;
      const txUtoV = (l.tx_u_to_v_pkts !== undefined) ? l.tx_u_to_v_pkts : 0;
      const txVtoU = (l.tx_v_to_u_pkts !== undefined) ? l.tx_v_to_u_pkts : 0;
      const avgQ = (l.avg_queueing_delay !== undefined) ? l.avg_queueing_delay : 0;
      const avgNet = (l.avg_network_latency !== undefined) ? l.avg_network_latency : 0;

      this.tooltip.innerHTML = `
        <div class="tooltip-header">
          <span class="badge ${isWrap ? "badge-allreduce" : "badge-scatter"}">${isWrap ? "Wrap-Around" : "Enlace Físico"}</span>
          <span class="tooltip-gpu">GPU ${u} ↔ GPU ${v}</span>
        </div>
        <div class="tooltip-body">
          <div class="tooltip-row"><span>Tipo y Latencia Base:</span> <strong>${typeText}</strong></div>
          <div class="tooltip-row"><span>Tráfico en Enlace:</span> <strong style="color:#ef4444;">${(l.packets || 0).toLocaleString()} pkts (${(l.flits || 0).toLocaleString()} flits)</strong></div>
          <div class="tooltip-row"><span>Cuota de Red:</span> <strong>${sharePct.toFixed(2)}% del clúster</strong></div>
          <div class="tooltip-row"><span>Balance Direccional:</span> <strong style="color:#38bdf8;">GPU ${u}→${v}: ${txUtoV.toLocaleString()} | GPU ${v}→${u}: ${txVtoU.toLocaleString()}</strong></div>
          <div class="tooltip-row"><span>Cola NIC Media:</span> <strong>${avgQ.toFixed(1)} ciclos</strong></div>
          <div class="tooltip-row"><span>Latencia Red Media:</span> <strong>${avgNet.toFixed(1)} ciclos</strong></div>
        </div>
      `;
    } else if (edge.type === "flow") {
      const f = edge.data;
      const hops = f.hops || 1;
      const totalClusterPkts = this.data.total_packets || 1;
      const sharePct = (f.share_pct !== undefined) ? f.share_pct : ((f.packets || 0) / totalClusterPkts * 100);
      const avgQ = (f.avg_queueing_delay !== undefined) ? f.avg_queueing_delay : (f.avg_queue || 0);
      const maxQ = (f.max_queueing_delay !== undefined) ? f.max_queueing_delay : avgQ;
      const avgNet = (f.avg_network_latency !== undefined) ? f.avg_network_latency : 0;
      const avgTot = (f.avg_total_latency !== undefined) ? f.avg_total_latency : (f.avg_latency || 0);

      this.tooltip.innerHTML = `
        <div class="tooltip-header">
          <span class="badge badge-gather">Flujo Directo</span>
          <span class="tooltip-gpu">GPU ${f.src} → GPU ${f.dst}</span>
        </div>
        <div class="tooltip-body">
          <div class="tooltip-row"><span>Distancia Topológica:</span> <strong>${hops} salto(s)</strong></div>
          <div class="tooltip-row"><span>Volumen Transferido:</span> <strong style="color:#f59e0b;">${(f.packets || 0).toLocaleString()} pkts (${(f.flits || 0).toLocaleString()} flits)</strong></div>
          <div class="tooltip-row"><span>Cuota de Tráfico:</span> <strong>${sharePct.toFixed(2)}% del tráfico</strong></div>
          <div class="tooltip-row"><span>Retardo en Cola NIC:</span> <strong>Media: ${avgQ.toFixed(1)} c | Pico: ${maxQ.toFixed(1)} c</strong></div>
          <div class="tooltip-row"><span>Vuelo / Contención NoC:</span> <strong>${avgNet.toFixed(1)} ciclos</strong></div>
          <div class="tooltip-row"><span>Latencia Total Flujo:</span> <strong style="color:#ef4444;">${avgTot.toFixed(1)} ciclos</strong></div>
        </div>
      `;
    }

    this.positionTooltip(clientX, clientY);
  }

  positionTooltip(clientX, clientY) {
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
