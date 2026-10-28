/** Lightweight SVG charts (area + radar) — no npm deps. */

function _el(tag, attrs = {}, kids = []) {
  const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, String(v)));
  kids.forEach((c) => n.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
  return n;
}

/**
 * @param {HTMLElement} host
 * @param {{ label: string, value: number }[]} points  value 0–100
 */
export function renderAreaChart(host, points) {
  host.innerHTML = "";
  const w = 560;
  const h = 240;
  const pad = { t: 18, r: 16, b: 36, l: 36 };
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;
  const data = points.length ? points : [
    { label: "第1次", value: 12 },
    { label: "第2次", value: 18 },
    { label: "第3次", value: 28 },
    { label: "第4次", value: 40 },
    { label: "最近", value: 48 },
  ];
  const svg = _el("svg", { viewBox: `0 0 ${w} ${h}`, width: "100%", height: "100%", class: "chart-svg" });
  const defs = _el("defs", {}, [
    _el("linearGradient", { id: "coachAreaFill", x1: "0", y1: "0", x2: "0", y2: "1" }, [
      _el("stop", { offset: "5%", "stop-color": "#1cbc8e", "stop-opacity": "0.4" }),
      _el("stop", { offset: "95%", "stop-color": "#f0b858", "stop-opacity": "0" }),
    ]),
  ]);
  svg.appendChild(defs);

  // grid
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (ih * i) / 4;
    svg.appendChild(_el("line", {
      x1: pad.l, y1: y, x2: pad.l + iw, y2: y,
      stroke: "#e8ecf1", "stroke-dasharray": "4 4",
    }));
    const v = 100 - i * 25;
    svg.appendChild(_el("text", {
      x: pad.l - 8, y: y + 4, "text-anchor": "end", fill: "#8b95a5", "font-size": "11",
    }, [String(v)]));
  }

  const n = data.length;
  const xy = data.map((d, i) => {
    const x = pad.l + (n === 1 ? iw / 2 : (iw * i) / (n - 1));
    const y = pad.t + ih * (1 - Math.max(0, Math.min(100, d.value)) / 100);
    return { x, y, ...d };
  });

  const line = xy.map((p, i) => `${i ? "L" : "M"}${p.x},${p.y}`).join(" ");
  const area = `${line} L${xy[xy.length - 1].x},${pad.t + ih} L${xy[0].x},${pad.t + ih} Z`;
  svg.appendChild(_el("path", { d: area, fill: "url(#coachAreaFill)" }));
  svg.appendChild(_el("path", { d: line, fill: "none", stroke: "#1cbc8e", "stroke-width": "2.5", "stroke-linejoin": "round" }));

  xy.forEach((p) => {
    svg.appendChild(_el("circle", { cx: p.x, cy: p.y, r: 3.5, fill: "#fff", stroke: "#1cbc8e", "stroke-width": "2" }));
    svg.appendChild(_el("text", {
      x: p.x, y: h - 12, "text-anchor": "middle", fill: "#8b95a5", "font-size": "11",
    }, [p.label]));
  });

  host.appendChild(svg);
}

/**
 * @param {HTMLElement} host
 * @param {{ axis: string, value: number, baseline?: number }[]} axes  value 0–100
 */
export function renderRadarChart(host, axes) {
  host.innerHTML = "";
  const items = (axes && axes.length ? axes : [
    { axis: "资料", value: 40, baseline: 30 },
    { axis: "大纲", value: 35, baseline: 30 },
    { axis: "陪练", value: 25, baseline: 30 },
    { axis: "掌握", value: 20, baseline: 30 },
    { axis: "答疑", value: 30, baseline: 30 },
  ]).slice(0, 8);

  const size = 340;
  const cx = size / 2;
  const cy = size / 2;
  const rMax = 110;
  const n = items.length;
  const angleAt = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
  const pt = (i, ratio) => {
    const a = angleAt(i);
    return [cx + Math.cos(a) * rMax * ratio, cy + Math.sin(a) * rMax * ratio];
  };

  const svg = _el("svg", { viewBox: `0 0 ${size} ${size}`, width: "100%", height: "100%", class: "chart-svg" });

  for (let ring = 1; ring <= 4; ring++) {
    const pts = Array.from({ length: n }, (_, i) => pt(i, ring / 4).join(",")).join(" ");
    svg.appendChild(_el("polygon", {
      points: pts, fill: "none", stroke: "#e8ecf1", "stroke-width": ring === 4 ? "1.2" : "1",
    }));
  }
  for (let i = 0; i < n; i++) {
    const [x, y] = pt(i, 1);
    svg.appendChild(_el("line", { x1: cx, y1: cy, x2: x, y2: y, stroke: "#eef1f5" }));
  }

  const baselinePts = items.map((it, i) => pt(i, Math.max(0, Math.min(100, it.baseline ?? 40)) / 100).join(",")).join(" ");
  svg.appendChild(_el("polygon", {
    points: baselinePts, fill: "rgba(235,168,72,0.12)", stroke: "#eba848", "stroke-width": "1.4",
  }));

  const valuePts = items.map((it, i) => pt(i, Math.max(0, Math.min(100, it.value)) / 100).join(",")).join(" ");
  svg.appendChild(_el("polygon", {
    points: valuePts, fill: "rgba(28,188,142,0.20)", stroke: "#1cbc8e", "stroke-width": "2",
  }));
  items.forEach((it, i) => {
    const [x, y] = pt(i, Math.max(0, Math.min(100, it.value)) / 100);
    svg.appendChild(_el("circle", { cx: x, cy: y, r: 3.2, fill: "#1cbc8e" }));
    const [lx, ly] = pt(i, 1.18);
    svg.appendChild(_el("text", {
      x: lx, y: ly, "text-anchor": "middle", "dominant-baseline": "middle",
      fill: "#1c2430", "font-size": "12", "font-weight": "650",
    }, [it.axis]));
  });

  host.appendChild(svg);
}

/**
 * CSS conic progress ring via style on host.
 * @param {HTMLElement} host  .progress-ring
 * @param {number} percent 0–100
 */
export function setProgressRing(host, percent) {
  const p = Math.max(0, Math.min(100, Number(percent) || 0));
  const deg = (p / 100) * 360;
  host.style.background = `conic-gradient(#1cbc8e ${deg}deg, #eef1f5 ${deg}deg)`;
  const span = host.querySelector("span");
  if (span) span.textContent = String(Math.round(p));
}
