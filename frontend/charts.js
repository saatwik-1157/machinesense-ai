/* ============================================================
   MachineSense AI - lightweight canvas charts (no dependencies)
   High-DPI aware. Provides: lineChart, healthGauge, donut, hbars
   ============================================================ */
const CSS = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

function setupCanvas(canvas, cssHeight) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || canvas.parentElement.clientWidth;
  const h = cssHeight || canvas.clientHeight || 200;
  canvas.style.height = h + "px";
  canvas.width = Math.max(1, Math.floor(w * dpr));
  canvas.height = Math.max(1, Math.floor(h * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}

/* Multi-series line chart.
   series = [{ data:[numbers], color:'#...', label, fill? }]  */
function lineChart(canvas, series, opts = {}) {
  const { ctx, w, h } = setupCanvas(canvas, opts.height);
  ctx.clearRect(0, 0, w, h);
  const padL = 42, padR = 12, padT = 12, padB = 22;
  const plotW = w - padL - padR, plotH = h - padT - padB;

  let min = opts.min, max = opts.max;
  if (min === undefined || max === undefined) {
    let lo = Infinity, hi = -Infinity;
    series.forEach(s => s.data.forEach(v => { if (v < lo) lo = v; if (v > hi) hi = v; }));
    if (lo === Infinity) { lo = 0; hi = 1; }
    const pad = (hi - lo) * 0.15 || 1;
    min = opts.min !== undefined ? opts.min : lo - pad;
    max = opts.max !== undefined ? opts.max : hi + pad;
  }
  const n = Math.max(...series.map(s => s.data.length), 1);
  const X = i => padL + (n <= 1 ? 0 : (i / (n - 1)) * plotW);
  const Y = v => padT + plotH - ((v - min) / (max - min || 1)) * plotH;

  // grid + y labels
  ctx.font = "11px 'Segoe UI', sans-serif";
  ctx.fillStyle = CSS("--faint");
  ctx.strokeStyle = CSS("--border-soft");
  ctx.lineWidth = 1;
  const rows = 4;
  for (let r = 0; r <= rows; r++) {
    const val = min + (max - min) * (r / rows);
    const y = Y(val);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    ctx.fillText(val.toFixed(val < 10 ? 1 : 0), padL - 7, y);
  }

  // threshold bands (optional)
  if (opts.warn !== undefined) drawThreshold(ctx, Y(opts.warn), w - padR, padL, CSS("--watch"), "warn");
  if (opts.critical !== undefined) drawThreshold(ctx, Y(opts.critical), w - padR, padL, CSS("--crit"), "critical");

  // series
  series.forEach(s => {
    if (s.data.length < 2) return;
    if (s.fill) {
      const g = ctx.createLinearGradient(0, padT, 0, padT + plotH);
      g.addColorStop(0, s.color + "44"); g.addColorStop(1, s.color + "02");
      ctx.beginPath(); ctx.moveTo(X(0), Y(s.data[0]));
      s.data.forEach((v, i) => ctx.lineTo(X(i), Y(v)));
      ctx.lineTo(X(s.data.length - 1), padT + plotH); ctx.lineTo(X(0), padT + plotH);
      ctx.closePath(); ctx.fillStyle = g; ctx.fill();
    }
    ctx.beginPath(); ctx.lineWidth = 2; ctx.strokeStyle = s.color;
    ctx.lineJoin = "round";
    s.data.forEach((v, i) => i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v)));
    ctx.stroke();
    // last-point dot
    const li = s.data.length - 1;
    ctx.beginPath(); ctx.arc(X(li), Y(s.data[li]), 3, 0, 7); ctx.fillStyle = s.color; ctx.fill();
  });
}

function drawThreshold(ctx, y, right, left, color, label) {
  ctx.save();
  ctx.strokeStyle = color; ctx.globalAlpha = .5; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
  ctx.restore();
}

/* Circular health gauge, value 0..100 */
function healthGauge(canvas, value, opts = {}) {
  const size = opts.size || 92;
  canvas.style.width = size + "px";
  const { ctx } = setupCanvas(canvas, size);
  canvas.width = size * (window.devicePixelRatio || 1);
  const dpr = window.devicePixelRatio || 1;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);
  const cx = size / 2, cy = size / 2, r = size / 2 - 8;
  const start = Math.PI * 0.75, end = Math.PI * 2.25;
  const frac = Math.max(0, Math.min(100, value)) / 100;

  const color = value >= 80 ? CSS("--good") : value >= 60 ? CSS("--watch")
              : value >= 40 ? CSS("--warn") : CSS("--crit");

  ctx.lineCap = "round";
  ctx.lineWidth = 8;
  ctx.strokeStyle = CSS("--panel-2");
  ctx.beginPath(); ctx.arc(cx, cy, r, start, end); ctx.stroke();

  ctx.strokeStyle = color;
  ctx.beginPath(); ctx.arc(cx, cy, r, start, start + (end - start) * frac); ctx.stroke();

  ctx.fillStyle = CSS("--text");
  ctx.font = `700 ${size * 0.26}px 'Segoe UI', sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(Math.round(value), cx, cy - 2);
  ctx.fillStyle = CSS("--faint");
  ctx.font = `600 ${size * 0.11}px 'Segoe UI', sans-serif`;
  ctx.fillText("HEALTH", cx, cy + size * 0.16);
}

/* Donut chart. segments = [{value, color, label}] */
function donut(canvas, segments, opts = {}) {
  const size = opts.size || 150;
  canvas.style.width = size + "px";
  const dpr = window.devicePixelRatio || 1;
  canvas.style.height = size + "px";
  canvas.width = size * dpr; canvas.height = size * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);
  const cx = size / 2, cy = size / 2, r = size / 2 - 6, thick = opts.thick || 22;
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  let ang = -Math.PI / 2;
  segments.forEach(s => {
    const slice = (s.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, r, ang, ang + slice);
    ctx.arc(cx, cy, r - thick, ang + slice, ang, true);
    ctx.closePath(); ctx.fillStyle = s.color; ctx.fill();
    ang += slice;
  });
  if (opts.centerText) {
    ctx.fillStyle = CSS("--text"); ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "700 20px 'Segoe UI', sans-serif";
    ctx.fillText(opts.centerText, cx, cy - 6);
    if (opts.centerSub) {
      ctx.fillStyle = CSS("--faint"); ctx.font = "600 10px 'Segoe UI', sans-serif";
      ctx.fillText(opts.centerSub, cx, cy + 12);
    }
  }
}
