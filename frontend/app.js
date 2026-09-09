/* ============================================================
   MachineSense AI - dashboard application
   Talks to the FastAPI backend when available; otherwise falls
   back to the in-browser LocalAPI simulator (simulator.js).
   If the backend disappears mid-session, the app degrades to
   demo mode seamlessly instead of freezing.
   ============================================================ */

// -------- API layer: backend first, local simulator fallback --------
const API = {
  useBackend: false,
  _demote() {
    // Backend became unreachable: flip to demo mode and say so.
    if (!this.useBackend) return;
    this.useBackend = false;
    const dot = $("#connDot"), txt = $("#connText");
    if (dot) { dot.className = "dot sim"; txt.textContent = "Demo mode · in-browser simulation"; }
  },
  async _try(path) {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);
    return res.json();
  },
  async _post(path, body) {
    const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(res.status);
    return res.json();
  },
  // fetch with graceful demotion: a network failure (server gone) switches to
  // the local simulator; HTTP errors (4xx) still propagate to the caller.
  _fetch(path, local) {
    if (!this.useBackend) return Promise.resolve(local());
    return this._try(path).catch(e => {
      if (e instanceof TypeError) { this._demote(); return local(); }
      throw e;
    });
  },
  _send(path, body, local) {
    if (!this.useBackend) return Promise.resolve(local());
    return this._post(path, body).catch(e => {
      if (e instanceof TypeError) { this._demote(); return local(); }
      throw e;
    });
  },
  async detect() {
    try { await this._try("/api/overview"); this.useBackend = true; }
    catch { this.useBackend = false; }
    return this.useBackend;
  },
  overview()          { return this._fetch("/api/overview", () => LocalAPI.overview()); },
  machine(id)         { return this._fetch(`/api/machines/${id}`, () => LocalAPI.machine(id)); },
  history(id, n = 60) { return this._fetch(`/api/machines/${id}/history?n=${n}`, () => LocalAPI.history(id, n)); },
  alerts()            { return this._fetch("/api/alerts", () => LocalAPI.alerts()); },
  meta()              { return this._fetch("/api/meta", () => LocalAPI.meta()); },
  twin(id, action)    { return this._send(`/api/machines/${id}/twin`, { action }, () => LocalAPI.twin(id, action)); },
  inject(id, fault)   { return this._send(`/api/machines/${id}/inject-fault`, { fault }, () => LocalAPI.inject(id, fault)); },
  repair(id)          { return this._send(`/api/machines/${id}/repair`, {}, () => LocalAPI.repair(id)); },
  power(id, running)  { return this._send(`/api/machines/${id}/power`, { running }, () => LocalAPI.power(id, running)); },
};

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmtINR = n => "₹" + Math.round(n).toLocaleString("en-IN");
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
// Escape anything API-derived before dropping it into innerHTML.
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const SENSOR_COLORS = { vibration: "#22d3ee", temperature: "#fb923c", current: "#a78bfa", sound: "#f43f5e", power: "#34d399" };

const state = { view: "overview", selectedMachine: "M-001", twinMachine: "M-002", meta: null, lastHist: null };

// ---------------- Router ----------------
const VIEW_META = {
  overview: ["Fleet Overview", "Real-time health of every connected machine"],
  machines: ["Machine Analytics", "Live sensors, predictions & explainable AI"],
  twin:     ["Digital Twin Simulator", "Validate maintenance decisions before you act"],
  energy:   ["Energy Optimization", "Consumption, efficiency and savings across the fleet"],
  alerts:   ["Alerts & Anomalies", "AI-detected issues that need attention"],
  about:    ["About the Project", "MachineSense AI — Smart India Hackathon 2026"],
};

function switchView(v) {
  state.view = v;
  $$("#nav button").forEach(b => b.classList.toggle("active", b.dataset.view === v));
  $$(".view").forEach(s => s.classList.toggle("active", s.id === `view-${v}`));
  $("#viewTitle").textContent = VIEW_META[v][0];
  $("#viewSub").textContent = VIEW_META[v][1];
  const main = $(".main");
  if (main) main.scrollTop = 0;  // each view starts at its top
  render(v);
}

$("#nav").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (btn) switchView(btn.dataset.view);
});

// ---------------- Clock ----------------
function tickClock() {
  const d = new Date();
  $("#clockTime").textContent = d.toLocaleTimeString("en-GB");
  $("#clockDate").textContent = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}
setInterval(tickClock, 1000); tickClock();

// ---------------- Rendering dispatch ----------------
async function render(v) {
  if (v === "overview") return renderOverview();
  if (v === "machines") return renderMachine(state.selectedMachine);
  if (v === "twin")     return renderTwin();
  if (v === "energy")   return renderEnergy();
  if (v === "alerts")   return renderAlerts();
  if (v === "about")    return renderAbout();
}

// ================= OVERVIEW =================
let _ovBusy = false;
async function renderOverview() {
  if (_ovBusy) return;          // don't stack refreshes
  _ovBusy = true;
  try {
    const o = await API.overview();
    renderKpis(o);
    renderMachineCards(o.machines);
    updateAlertBadge(o.active_alerts);
  } catch (e) { /* transient fetch issue — next tick retries */ }
  finally { _ovBusy = false; }
}

function kpiData(o) {
  return [
    { label: "Fleet Health", value: o.avg_health + "%", sub: `${o.fleet_size} machines monitored`, color: bandColor(o.avg_health), ico: icoHeart },
    { label: "Machines at Risk", value: o.machines_at_risk, sub: o.machines_at_risk ? "Need attention" : "All nominal", color: o.machines_at_risk ? "var(--crit)" : "var(--good)", ico: icoWarn },
    { label: "Active Alerts", value: o.active_alerts, sub: "AI-detected anomalies", color: o.active_alerts ? "var(--warn)" : "var(--good)", ico: icoBell },
    { label: "Est. Monthly Savings", value: fmtINR(o.energy.potential_monthly_savings_inr), sub: "via energy optimization", color: "var(--accent)", ico: icoBolt },
  ];
}

function renderKpis(o) {
  const kpis = kpiData(o);
  const box = $("#kpis");
  const cards = box.querySelectorAll(".kpi");
  if (cards.length === kpis.length) {
    // Update in place: no DOM churn, no flicker.
    kpis.forEach((k, i) => {
      const v = cards[i].querySelector(".value");
      v.textContent = k.value; v.style.color = k.color;
      cards[i].querySelector(".sub").textContent = k.sub;
    });
    return;
  }
  box.innerHTML = kpis.map(k => `
    <div class="card kpi">
      <div class="label">${k.label}</div>
      <div class="value" style="color:${k.color}">${k.value}</div>
      <div class="sub">${k.sub}</div>
      <div class="ico">${k.ico}</div>
    </div>`).join("");
}

function renderMachineCards(machines) {
  const box = $("#overviewMachines");
  const existing = box.querySelectorAll(".mcard");
  const sameSet = existing.length === machines.length &&
    machines.every((m, i) => existing[i].dataset.id === m.id);
  if (sameSet) {
    // Update chips/runtime/gauges in place so hover states and clicks survive.
    machines.forEach((m, i) => {
      existing[i].querySelector(".mfoot").innerHTML = machineFoot(m);
      healthGauge($(`#g-${m.id}`), m.health, { size: 68 });
    });
    return;
  }
  box.innerHTML = machines.map(m => machineCard(m)).join("");
  machines.forEach(m => healthGauge($(`#g-${m.id}`), m.health, { size: 68 }));
}

function machineFoot(m) {
  return `
    <span class="chip ${m.band}"><span class="cd"></span>${cap(m.band)}</span>
    ${m.fault ? `<span class="chip critical">⚠ ${esc(m.fault)}</span>` : ""}
    ${!m.running ? `<span class="chip ghost">■ Stopped</span>` : ""}
    <span class="status-line" style="margin-left:auto">${Math.round(m.runtime_hours).toLocaleString()} h runtime</span>`;
}

function machineCard(m) {
  return `<div class="card mcard" data-id="${m.id}" tabindex="0" role="button" aria-label="Open ${esc(m.name)} analytics">
    <div class="mhead">
      <div>
        <div class="mname">${esc(m.name)}</div>
        <div class="mmeta">${m.id} · ${esc(m.type)} · ${esc(m.location)}</div>
      </div>
      <div class="gauge-wrap"><canvas id="g-${m.id}"></canvas></div>
    </div>
    <div class="mfoot">${machineFoot(m)}</div>
  </div>`;
}

// One delegated listener on the stable container: clicks can't be swallowed
// by refresh-time DOM replacement, and cards work with the keyboard too.
function openCardFrom(e) {
  const card = e.target.closest(".mcard");
  if (!card) return;
  state.selectedMachine = card.dataset.id;
  switchView("machines");
}
$("#overviewMachines").addEventListener("click", openCardFrom);
$("#overviewMachines").addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openCardFrom(e); }
});

// ================= MACHINE DETAIL =================
async function renderMachine(id) {
  const o = await API.overview();
  const options = o.machines.map(m => `<option value="${m.id}" ${m.id === id ? "selected" : ""}>${esc(m.name)} (${m.id})</option>`).join("");
  const d = await API.machine(id);
  const hist = await API.history(id, 60);
  if (id !== state.selectedMachine) return;  // user moved on while we fetched
  state.lastHist = hist;

  const p = d.prediction;

  $("#machineDetail").innerHTML = `
    <div class="toolbar">
      <select class="input" id="machineSelect">${options}</select>
      <span id="statusChips">${statusChips(d)}</span>
      <div style="margin-left:auto; display:flex; gap:8px">
        <button class="btn sm" id="btnPower">${d.running ? "⏻ Stop Machine" : "▶ Start Machine"}</button>
        <button class="btn sm" id="btnRepair">🔧 Simulate Repair</button>
        <button class="btn sm danger" id="btnFault">⚡ Inject Fault</button>
      </div>
    </div>

    <div class="grid detail-grid">
      <div class="card chart-box">
        <h3 class="ct">${icoWave} Live Sensor Telemetry</h3>
        <canvas id="sensorChart"></canvas>
        <div class="legend" id="sensorLegend"></div>
        <div class="sub-note">Streaming at 0.5 Hz · values normalized to % of each sensor's critical threshold · dashed line = critical (100%)</div>
      </div>

      <div class="card">
        <h3 class="ct">${icoGauge} Prediction</h3>
        <div class="mini">
          <div class="box"><div class="l">Remaining Life</div><div class="v" id="predRul">${rulLabel(p)}</div></div>
          <div class="box"><div class="l">Failure Risk</div><div class="v" id="predRisk" style="color:${riskColor(p.failure_probability)}">${Math.round(p.failure_probability * 100)}%</div></div>
        </div>
        <div class="mini" style="margin-top:10px">
          <div class="box"><div class="l">Health Trend</div><div class="v" id="predTrend">${p.trend_per_hour} <small>/h</small></div></div>
          <div class="box"><div class="l">Confidence</div><div class="v" id="predConf">${Math.round(p.confidence * 100)}%</div></div>
        </div>
        <div style="margin-top:16px"><canvas id="healthChart"></canvas></div>
      </div>
    </div>

    <div class="grid detail-grid" style="margin-top:16px">
      <div class="card">
        <h3 class="ct">${icoWave} Sensor Readings</h3>
        <div id="sensorBars">${sensorBarsHtml(d)}</div>
      </div>
      <div class="card">
        <h3 class="ct">${icoBrain} Explainable AI — Why this score?</h3>
        <ul class="reasons" id="xaiReasons">${xaiReasonsHtml(d)}</ul>
        <div class="section-title" style="margin:14px 2px 8px">Health impact by sensor</div>
        <div id="contribBars">${contribBarsHtml(d)}</div>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <h3 class="ct">${icoWrench} Recommended Actions</h3>
      <div id="recs">${recsHtml(d)}</div>
    </div>`;

  drawSensorChart(hist);
  drawHealthChart(hist);

  $("#machineSelect").addEventListener("change", e => { state.selectedMachine = e.target.value; renderMachine(e.target.value); });
  $("#btnPower").addEventListener("click", async () => { await API.power(id, !d.running); renderMachine(id); });
  $("#btnRepair").addEventListener("click", async () => { await API.repair(id); renderMachine(id); });
  $("#btnFault").addEventListener("click", async () => {
    const faults = Object.keys(state.meta.faults);
    await API.inject(id, faults[Math.floor(Math.random() * faults.length)]); renderMachine(id);
  });
}

function rulLabel(p) { return p.rul_hours >= 1900 ? "Stable" : `${p.rul_days.toFixed(1)} days`; }

function statusChips(d) {
  return `
    <span class="chip ${d.band}"><span class="cd"></span>${cap(d.band)} · ${d.health}%</span>
    ${d.fault ? `<span class="chip critical">⚠ ${esc(d.fault)}</span>` : ""}
    ${!d.running ? `<span class="chip ghost">■ Stopped</span>` : ""}`;
}

function sensorRow(s, c) {
  const pct = Math.min(100, (c.value / c.critical) * 100);
  const col = c.value >= c.critical ? "var(--crit)" : c.value >= c.warn ? "var(--warn)" : "var(--good)";
  return { pct, col };
}
function sensorBarsHtml(d) {
  return Object.entries(d.sensors).map(([s, c]) => {
    const { pct, col } = sensorRow(s, c);
    return `<div class="sensor-row" data-sensor="${s}">
      <div class="sname">${s}</div>
      <div class="sval" style="color:${col}">${c.value}${c.unit}</div>
      <div class="bar"><i style="width:${pct}%;background:${col}"></i></div>
    </div>`;
  }).join("");
}
function updateSensorBars(d) {
  const box = $("#sensorBars"); if (!box) return;
  const rows = box.querySelectorAll(".sensor-row");
  const entries = Object.entries(d.sensors);
  if (rows.length !== entries.length) { box.innerHTML = sensorBarsHtml(d); return; }
  // In-place update lets the CSS width transition actually animate.
  entries.forEach(([s, c], i) => {
    const { pct, col } = sensorRow(s, c);
    const val = rows[i].querySelector(".sval");
    val.textContent = `${c.value}${c.unit}`; val.style.color = col;
    const bar = rows[i].querySelector(".bar > i");
    bar.style.width = pct + "%"; bar.style.background = col;
  });
}
function xaiReasonsHtml(d) { return d.explanation.reasons.map(r => `<li>${esc(r)}</li>`).join(""); }
function contribBarsHtml(d) {
  return d.explanation.contributions.map(c => {
    const col = c.status === "critical" ? "var(--crit)" : c.status === "warn" ? "var(--warn)" : "var(--accent)";
    return `<div class="sensor-row">
      <div class="sname">${c.sensor}</div>
      <div class="sval">${c.contribution_pct}%</div>
      <div class="bar"><i style="width:${Math.min(100, c.contribution_pct * 3)}%;background:${col}"></i></div>
    </div>`;
  }).join("");
}
function recsHtml(d) {
  return d.recommendations.map(r => `
    <div class="rec">
      <span class="prio ${r.priority}">${r.priority}</span>
      <div><div class="ractn">${esc(r.action)}</div>
      <div class="sub-note" style="margin-top:3px">Driver: ${cap(esc(r.driver))}</div></div>
    </div>`).join("");
}

function drawSensorChart(hist) {
  const pts = hist.points;
  const series = ["vibration", "temperature", "current", "sound", "power"].map(s => ({
    label: s, color: SENSOR_COLORS[s], data: pts.map(p => normalize(s, p[s])),
  }));
  lineChart($("#sensorChart"), series, { height: 210, min: 0, max: 108, critical: 100 });
  $("#sensorLegend").innerHTML = series.map(s =>
    `<span><i style="background:${s.color}"></i>${cap(s.label)}</span>`).join("") +
    `<span style="margin-left:auto;color:var(--faint)">values normalized to % of critical threshold</span>`;
}
function normalize(s, v) {
  // Prefer the thresholds the active API reported; fall back to the local mirror.
  const c = (state.meta && state.meta.sensors && state.meta.sensors[s]) || window.MS_SENSORS[s];
  return Math.min(108, (v / c.critical) * 100);
}

function drawHealthChart(hist) {
  const data = hist.points.map(p => p.health);
  lineChart($("#healthChart"), [{ label: "health", color: "#22d3ee", data, fill: true }], { height: 90, min: 0, max: 100 });
}

// ================= DIGITAL TWIN =================
async function renderTwin() {
  const o = await API.overview();
  const options = o.machines.map(m => `<option value="${m.id}" ${m.id === state.twinMachine ? "selected" : ""}>${esc(m.name)} (${m.id})</option>`).join("");
  const actions = state.meta.twin_actions;
  const actionLabels = { preventive_maintenance: "Preventive Maintenance", bearing_replacement: "Bearing Replacement", lubrication: "Lubrication Service", cooling_service: "Cooling System Service", electrical_service: "Electrical Service", no_action: "No Action (baseline)" };

  $("#twinView").innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <h3 class="ct">${icoTwin} What-If Simulation</h3>
      <p class="muted" style="font-size:13px;margin-bottom:14px">
        The digital twin projects the effect of a maintenance action on health, remaining life, failure risk and energy —
        <b>before</b> you touch the real machine. This de-risks every maintenance decision.</p>
      <div class="toolbar" style="margin:0">
        <select class="input" id="twinMachine">${options}</select>
        <select class="input" id="twinAction">${actions.map(a => `<option value="${a}">${actionLabels[a] || esc(a)}</option>`).join("")}</select>
        <button class="btn primary" id="btnTwin">▶ Run Simulation</button>
      </div>
    </div>
    <div id="twinResult"></div>`;

  $("#twinMachine").addEventListener("change", e => { state.twinMachine = e.target.value; runTwin(); });
  $("#twinAction").addEventListener("change", runTwin);
  $("#btnTwin").addEventListener("click", runTwin);
  runTwin();
}

async function runTwin() {
  const mSel = $("#twinMachine"), aSel = $("#twinAction");
  if (!mSel || !aSel) return;
  const id = mSel.value, action = aSel.value;
  state.twinMachine = id;
  let r;
  try { r = await API.twin(id, action); } catch (e) { return; }
  if (!r || !$("#twinResult")) return;
  const dH = r.delta.health, dR = r.delta.rul_hours;
  const dF = Math.round((r.after.failure_probability - r.before.failure_probability) * 100);
  // When both sides sit at the "stable" sentinel (>=1900h), a raw hour delta
  // would contradict the two "Stable" labels — show a dash instead.
  const bothStable = r.before.rul_hours >= 1900 && r.after.rul_hours >= 1900;
  $("#twinResult").innerHTML = `
    <div class="grid twin-cols">
      ${twinPanel("Before (current state)", r.before, "var(--muted)")}
      ${twinPanel("After (projected)", r.after, "var(--accent)")}
    </div>
    <div class="card" style="margin-top:16px">
      <h3 class="ct">${icoBolt} Projected Impact</h3>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(180px,1fr))">
        ${impactBox("Health Score", (dH >= 0 ? "+" : "") + dH + " pts", dH >= 0)}
        ${impactBox("Remaining Life", bothStable ? "— (already stable)" : (dR >= 0 ? "+" : "") + Math.round(dR / 16) + " days", dR >= 0)}
        ${impactBox("Failure Risk", (dF > 0 ? "+" : "") + dF + "%", dF <= 0)}
        ${impactBox("Energy Savings", fmtINR(r.delta.monthly_energy_savings_inr) + "/mo", r.delta.monthly_energy_savings_inr >= 0)}
      </div>
      <div class="sub-note">Simulation only — no changes applied to the physical asset. Recommended when projected health gain is positive and failure risk drops.</div>
    </div>`;
  // Same response paints panels AND gauges — they can never disagree.
  healthGauge($("#tw-b"), r.before.health, { size: 100 });
  healthGauge($("#tw-a"), r.after.health, { size: 100 });
}

function twinPanel(title, s, color) {
  return `<div class="card tw-panel">
    <h4>${title}</h4>
    <canvas id="tw-${title.includes("Before") ? "b" : "a"}" width="100" height="100" style="width:100px;height:100px;display:block;margin:0 auto 8px"></canvas>
    <div class="tw-stat"><span>Health</span><b style="color:${color}">${s.health}%</b></div>
    <div class="tw-stat"><span>Remaining Life</span><b>${s.rul_hours >= 1900 ? "Stable" : Math.round(s.rul_hours / 16) + " d"}</b></div>
    <div class="tw-stat"><span>Failure Risk</span><b>${Math.round(s.failure_probability * 100)}%</b></div>
  </div>`;
}
function impactBox(label, val, good) {
  return `<div class="mini" style="margin:0"><div class="box" style="text-align:center">
    <div class="l">${label}</div>
    <div class="v"><span class="delta-badge ${good ? "up" : "down"}">${val}</span></div>
  </div></div>`;
}

// ================= ENERGY =================
let _enBusy = false;
async function renderEnergy() {
  if (_enBusy) return;
  _enBusy = true;
  try {
    const o = await API.overview();
    const details = await Promise.all(o.machines.map(m => API.machine(m.id)));
    if (state.view !== "energy") return;
    const totalCost = o.energy.monthly_cost_inr, savings = o.energy.potential_monthly_savings_inr, co2 = o.energy.co2_kg_month;
    const pctOfSpend = totalCost ? Math.round(savings / totalCost * 100) : 0;

    $("#energyView").innerHTML = `
      <div class="grid kpis" style="margin-bottom:18px">
        <div class="card kpi"><div class="label">Monthly Energy Cost</div><div class="value">${fmtINR(totalCost)}</div><div class="sub">across ${o.fleet_size} machines</div><div class="ico">${icoBolt}</div></div>
        <div class="card kpi"><div class="label">Recoverable Waste</div><div class="value" style="color:var(--good)">${fmtINR(savings)}</div><div class="sub">${pctOfSpend}% of spend</div><div class="ico">${icoLeaf}</div></div>
        <div class="card kpi"><div class="label">CO₂ Footprint</div><div class="value">${(co2 / 1000).toFixed(1)}t</div><div class="sub">per month</div><div class="ico">${icoLeaf}</div></div>
        <div class="card kpi"><div class="label">Annual Savings Potential</div><div class="value" style="color:var(--accent)">${fmtINR(savings * 12)}</div><div class="sub">if waste eliminated</div><div class="ico">${icoBolt}</div></div>
      </div>

      <div class="grid detail-grid">
        <div class="card">
          <h3 class="ct">${icoBolt} Power Draw by Machine</h3>
          <div id="energyBars"></div>
        </div>
        <div class="card">
          <h3 class="ct">${icoLeaf} Efficiency Distribution</h3>
          <div class="donut-row">
            <canvas id="effDonut"></canvas>
            <div id="effLegend" style="font-size:13px"></div>
          </div>
        </div>
      </div>`;

    const maxPower = Math.max(...details.map(d => d.energy.avg_power_kw || 0));
    $("#energyBars").innerHTML = details.map(d => {
      const e = d.energy, pct = maxPower ? (e.avg_power_kw / maxPower) * 100 : 0;
      const col = e.efficiency_pct >= 85 ? "var(--good)" : e.efficiency_pct >= 70 ? "var(--watch)" : "var(--warn)";
      return `<div class="sensor-row">
        <div class="sname" style="width:130px">${esc(d.name)}</div>
        <div class="sval">${e.avg_power_kw} kW</div>
        <div class="bar"><i style="width:${pct}%;background:${col}"></i></div>
        <div style="width:56px;text-align:right;font-size:12px;color:${col}">${e.efficiency_pct}%</div>
      </div>`;
    }).join("");

    const buckets = { "High (≥85%)": 0, "Fair (70-85%)": 0, "Low (<70%)": 0 };
    details.forEach(d => { const e = d.energy.efficiency_pct; if (e >= 85) buckets["High (≥85%)"]++; else if (e >= 70) buckets["Fair (70-85%)"]++; else buckets["Low (<70%)"]++; });
    const segs = [
      { label: "High (≥85%)", value: buckets["High (≥85%)"], color: "#34d399" },
      { label: "Fair (70-85%)", value: buckets["Fair (70-85%)"], color: "#fbbf24" },
      { label: "Low (<70%)", value: buckets["Low (<70%)"], color: "#fb923c" },
    ];
    donut($("#effDonut"), segs, { size: 150, centerText: o.fleet_size, centerSub: "MACHINES" });
    $("#effLegend").innerHTML = segs.map(s => `<div style="display:flex;align-items:center;gap:8px;margin:6px 0"><i style="width:12px;height:12px;border-radius:3px;background:${s.color};display:inline-block"></i>${s.label}: <b>${s.value}</b></div>`).join("");
  } catch (e) { /* transient fetch issue — next tick retries */ }
  finally { _enBusy = false; }
}

// ================= ALERTS =================
// First-seen tracking so alert ages are real, not a hardcoded "just now".
const _alertSeen = new Map();
function alertAge(key) {
  const now = Date.now();
  if (!_alertSeen.has(key)) _alertSeen.set(key, now);
  const mins = Math.round((now - _alertSeen.get(key)) / 60000);
  return mins < 1 ? "just now" : mins < 60 ? `${mins}m ago` : `${Math.floor(mins / 60)}h ${mins % 60}m ago`;
}

async function renderAlerts() {
  let alerts;
  try { alerts = await API.alerts(); } catch (e) { return; }
  if (!$("#alertsView")) return;
  updateAlertBadge(alerts.length);
  const liveKeys = new Set(alerts.map(a => `${a.machine_id}|${a.sensor}|${a.kind}`));
  [..._alertSeen.keys()].forEach(k => { if (!liveKeys.has(k)) _alertSeen.delete(k); });
  if (!alerts.length) {
    $("#alertsView").innerHTML = `<div class="card"><div class="empty">✓ No active anomalies. Every machine is operating within normal limits.</div></div>`;
    return;
  }
  $("#alertsView").innerHTML = `<div class="card">
    <h3 class="ct">${icoBell} ${alerts.length} Active Alert${alerts.length > 1 ? "s" : ""}</h3>
    ${alerts.map(a => `
      <div class="alert-item ${a.level}">
        <div class="aico">${a.level === "critical" ? icoWarn : icoBell}</div>
        <div>
          <div class="amsg">${esc(a.message)}</div>
          <div class="ameta">${a.machine_id} · severity ${Math.round(a.severity * 100)}% · ${cap(a.level)}</div>
        </div>
        <div class="atime">${alertAge(`${a.machine_id}|${a.sensor}|${a.kind}`)}</div>
      </div>`).join("")}
  </div>`;
}

// ================= ABOUT =================
function renderAbout() {
  const features = [
    [icoWave, "Real-time Monitoring", "Continuous IoT streaming of vibration, temperature, current, sound and power from every asset."],
    [icoGauge, "Predictive Maintenance", "Remaining-useful-life & failure-probability forecasts from live degradation trends."],
    [icoBrain, "Explainable AI", "Every health score is broken down by sensor with plain-language root-cause reasoning."],
    [icoBolt, "Energy Optimization", "Detects waste and quantifies recoverable cost and CO₂ across the fleet."],
    [icoTwin, "Digital Twin", "Validate maintenance actions in simulation before applying them to real machines."],
    [icoBell, "Smart Alerts", "Robust anomaly detection flags issues the moment sensor behaviour deviates."],
  ];
  const stack = ["ESP32 + IoT sensors", "Python", "FastAPI", "React-ready frontend", "PostgreSQL", "Docker", "Time-series ML", "Anomaly detection"];
  const apps = ["Manufacturing", "Automotive", "Food Processing", "Pharmaceuticals", "Textile", "Packaging", "CNC Workshops", "Logistics", "Electronics"];

  $("#aboutView").innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <h3 class="ct">${icoInfo} MachineSense AI</h3>
      <p class="muted" style="font-size:13.5px;line-height:1.6;max-width:820px">
        An Industry 4.0 platform that combines IoT sensors, Explainable AI, predictive maintenance, energy optimization
        and digital-twin simulation to help <b>Indian industry</b> reduce downtime, maintenance cost and energy consumption —
        making advanced industrial intelligence affordable and accessible.</p>
    </div>

    <div class="section-title">Core Capabilities</div>
    <div class="grid about-grid">
      ${features.map(f => `<div class="card feature"><div class="fico">${f[0]}</div><div><h5>${f[1]}</h5><p>${f[2]}</p></div></div>`).join("")}
    </div>

    <div class="card" style="margin-top:16px">
      <h3 class="ct">${icoTwin} System Architecture</h3>
      <div class="arch-flow">
        ${["Industrial Machines", "IoT Sensors", "Edge Gateway", "Cloud", "AI Engine", "Digital Twin", "Recommendations", "Dashboard"]
          .map((n, i, a) => `<span class="node">${n}</span>${i < a.length - 1 ? '<span class="arrow">→</span>' : ""}`).join("")}
      </div>
    </div>

    <div class="grid detail-grid" style="margin-top:16px">
      <div class="card">
        <h3 class="ct">${icoWrench} Technology Stack</h3>
        <div class="pill-row">${stack.map(s => `<span class="pill">${s}</span>`).join("")}</div>
      </div>
      <div class="card">
        <h3 class="ct">${icoInfo} Target Applications</h3>
        <div class="pill-row">${apps.map(s => `<span class="pill">${s}</span>`).join("")}</div>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <h3 class="ct">${icoBolt} Project at a Glance</h3>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
        <div class="mini" style="margin:0"><div class="box"><div class="l">Domain</div><div class="v" style="font-size:15px">Industry 4.0</div></div></div>
        <div class="mini" style="margin:0"><div class="box"><div class="l">Event</div><div class="v" style="font-size:15px">SIH 2026</div></div></div>
        <div class="mini" style="margin:0"><div class="box"><div class="l">Category</div><div class="v" style="font-size:15px">Software</div></div></div>
        <div class="mini" style="margin:0"><div class="box"><div class="l">Status</div><div class="v" style="font-size:15px">Working Prototype</div></div></div>
      </div>
      <div class="sub-note">Smart India Hackathon 2026 · Explainable Industrial Intelligence for Predictive Maintenance, Digital Twin & Energy Optimization</div>
    </div>`;
}

// ---------------- helpers ----------------
function bandColor(h) { return h >= 80 ? "var(--good)" : h >= 60 ? "var(--watch)" : h >= 40 ? "var(--warn)" : "var(--crit)"; }
function riskColor(p) { return p >= 0.7 ? "var(--crit)" : p >= 0.4 ? "var(--warn)" : "var(--good)"; }
function updateAlertBadge(n) {
  const b = $("#alertBadge");
  if (n > 0) { b.style.display = ""; b.textContent = n; } else b.style.display = "none";
}

// ---------------- Icons (inline SVG strings) ----------------
const icoHeart = `<svg viewBox="0 0 24 24" fill="none" stroke="var(--good)" stroke-width="2"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>`;
const icoWarn = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>`;
const icoBell = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"/></svg>`;
const icoBolt = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2 3 14h9l-1 8 10-12h-9z"/></svg>`;
const icoWave = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12h3l3-8 4 16 3-8h5"/></svg>`;
const icoGauge = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 14 15 9M3.5 18a9 9 0 1 1 17 0"/><circle cx="12" cy="14" r="1.5"/></svg>`;
const icoBrain = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3a3 3 0 0 0-3 3 3 3 0 0 0-1 5.8V15a3 3 0 0 0 4 2.8A3 3 0 0 0 12 20V4a3 3 0 0 0-3-1zM15 3a3 3 0 0 1 3 3 3 3 0 0 1 1 5.8V15a3 3 0 0 1-4 2.8"/></svg>`;
const icoWrench = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a4 4 0 0 1-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 1 5.4-5.4l-2.3 2.3-2-2 2.3-2.3z"/></svg>`;
const icoTwin = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="9" height="16" rx="1"/><rect x="13" y="4" width="9" height="16" rx="1"/></svg>`;
const icoLeaf = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 20A7 7 0 0 1 4 13c0-5 4-9 16-9 0 8-4 12-9 12M4 20c2-4 5-6 9-7"/></svg>`;
const icoInfo = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>`;

// ---------------- Boot ----------------
async function boot() {
  await API.detect();
  const dot = $("#connDot"), txt = $("#connText");
  if (API.useBackend) { dot.className = "dot live"; txt.textContent = "Live · FastAPI backend"; }
  else { dot.className = "dot sim"; txt.textContent = "Demo mode · in-browser simulation"; }

  try { state.meta = await API.meta(); }
  catch { state.meta = LocalAPI.meta(); }
  switchView("overview");

  // Live refresh of the active view; the sidebar alert badge stays fresh on
  // every view. All branches swallow transient errors — the next tick retries.
  setInterval(() => {
    if (state.view !== "overview" && state.view !== "alerts") {
      API.alerts().then(a => updateAlertBadge(a.length)).catch(() => {});
    }
    if (state.view === "overview") renderOverview();
    else if (state.view === "machines") refreshMachineCharts();
    else if (state.view === "alerts") renderAlerts();
    else if (state.view === "energy") renderEnergy();
  }, 2500);
}

let _mchBusy = false;
async function refreshMachineCharts() {
  const c0 = $("#sensorChart");
  if (!c0 || !c0.clientWidth) return;   // view hidden or not yet built
  if (_mchBusy) return;
  _mchBusy = true;
  const id = state.selectedMachine;
  try {
    const [d, hist] = await Promise.all([API.machine(id), API.history(id, 60)]);
    // Bail on stale responses: user may have switched machine or view mid-fetch.
    if (id !== state.selectedMachine) return;
    const c = $("#sensorChart");
    if (!c || !c.clientWidth) return;
    state.lastHist = hist;
    drawSensorChart(hist);
    drawHealthChart(hist);
    updateSensorBars(d);
    // Keep prediction, chips, XAI and recommendations live too.
    const p = d.prediction;
    if ($("#predRul"))   $("#predRul").textContent = rulLabel(p);
    if ($("#predRisk")) { $("#predRisk").textContent = Math.round(p.failure_probability * 100) + "%"; $("#predRisk").style.color = riskColor(p.failure_probability); }
    if ($("#predTrend")) $("#predTrend").innerHTML = `${p.trend_per_hour} <small>/h</small>`;
    if ($("#predConf"))  $("#predConf").textContent = Math.round(p.confidence * 100) + "%";
    if ($("#statusChips")) $("#statusChips").innerHTML = statusChips(d);
    if ($("#xaiReasons"))  $("#xaiReasons").innerHTML = xaiReasonsHtml(d);
    if ($("#contribBars")) $("#contribBars").innerHTML = contribBarsHtml(d);
    if ($("#recs"))        $("#recs").innerHTML = recsHtml(d);
  } catch (e) { /* transient fetch issue — next tick retries */ }
  finally { _mchBusy = false; }
}

// Debounced: redraw from cached data — a resize changes geometry, not data.
let _resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(() => {
    if (state.view === "machines" && state.lastHist && $("#sensorChart")) {
      drawSensorChart(state.lastHist);
      drawHealthChart(state.lastHist);
    }
  }, 150);
});
boot();
