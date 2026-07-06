/* ============================================================
   MachineSense AI - client-side fallback simulator
   Mirrors the FastAPI backend so the dashboard is fully functional
   even when opened as a static file (file://) with no server.
   Produces the same JSON shapes the REST API returns.
   ============================================================ */
const SENSORS = {
  vibration:   { unit: "mm/s", baseline: 2.0,  warn: 4.5,  critical: 7.1,  weight: 0.30 },
  temperature: { unit: "°C",   baseline: 55.0, warn: 75.0, critical: 90.0, weight: 0.25 },
  current:     { unit: "A",    baseline: 12.0, warn: 16.0, critical: 20.0, weight: 0.15 },
  sound:       { unit: "dB",   baseline: 72.0, warn: 85.0, critical: 95.0, weight: 0.15 },
  power:       { unit: "kW",   baseline: 7.5,  warn: 10.5, critical: 13.0, weight: 0.15 },
};
const RATED_POWER_KW = 9.0;
const FAULTS = {
  bearing_wear:        { label: "Bearing Wear",         bias: { vibration: 3.4, sound: 8.0, temperature: 6.0 } },
  overheating:         { label: "Overheating",          bias: { temperature: 22.0, current: 3.0, power: 2.2 } },
  electrical_overload: { label: "Electrical Overload",  bias: { current: 6.0, power: 4.0, temperature: 5.0 } },
  misalignment:        { label: "Shaft Misalignment",   bias: { vibration: 2.6, sound: 5.0 } },
  lubrication_loss:    { label: "Lubrication Loss",     bias: { temperature: 9.0, vibration: 1.8, sound: 4.0 } },
};

const _cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;

let _seed = 987654321;
function rnd() { _seed = (_seed * 1103515245 + 12345) & 0x7fffffff; return _seed / 0x7fffffff; }
function gauss(m, s) { return m + s * (rnd() + rnd() + rnd() - 1.5) * 1.2; }

class Machine {
  constructor(id, name, type, location, degr, days) {
    this.id = id; this.name = name; this.type = type; this.location = location;
    this.degradation = degr; this.trueHealth = 0.8 + rnd() * 0.19;
    this.fault = null; this.faultSeverity = 0; this.running = true;
    this.history = []; this.runtime = days * (9 + rnd() * 6);
    this.t0 = Date.now();
  }
}

class LocalFleet {
  constructor() {
    this.machines = {};
    [
      ["M-001", "CNC Milling Machine", "CNC", "Shop Floor A", 0.00040, 620],
      ["M-002", "Air Compressor", "Compressor", "Utility Room", 0.00055, 810],
      ["M-003", "Injection Moulder", "Moulding", "Shop Floor B", 0.00048, 430],
      ["M-004", "Conveyor Motor", "Motor", "Packaging Line", 0.00030, 350],
      ["M-005", "Hydraulic Press", "Press", "Shop Floor A", 0.00060, 900],
      ["M-006", "Cooling Pump", "Pump", "Utility Room", 0.00038, 540],
    ].forEach(s => { this.machines[s[0]] = new Machine(...s); });
    for (let i = 0; i < 60; i++) this.tick(true);
    // Apply demo faults after warm-up so they start fresh, not flatlined.
    this.machines["M-002"].fault = "bearing_wear"; this.machines["M-002"].faultSeverity = 0.5;  this.machines["M-002"].trueHealth = 0.5;
    this.machines["M-005"].fault = "overheating";  this.machines["M-005"].faultSeverity = 0.28; this.machines["M-005"].trueHealth = 0.68;
    // Reflect the seeded faults in the latest readings straight away.
    for (let i = 0; i < 8; i++) this.tick();
  }

  tick() {
    for (const m of Object.values(this.machines)) {
      if (m.running) {
        m.runtime += 0.25;
        let wear = m.degradation;
        if (m.fault) { m.faultSeverity = Math.min(1, m.faultSeverity + 0.0004 + rnd() * 0.0014); wear += m.faultSeverity * 0.0012; }
        m.trueHealth = Math.max(0, m.trueHealth - wear);
      }
      m.history.push(this._read(m));
      if (m.history.length > 240) m.history.shift();
    }
  }

  _read(m) {
    const out = { t: Math.round((Date.now() - m.t0) / 1000) };
    const deficit = 1 - Math.max(0, Math.min(1, m.trueHealth));
    for (const [s, cfg] of Object.entries(SENSORS)) {
      if (!m.running) { out[s] = (s === "temperature") ? 22 : 0; continue; }
      const span = cfg.critical - cfg.baseline;
      let v = cfg.baseline + span * deficit * 0.85;
      if (m.fault && FAULTS[m.fault].bias[s]) v += FAULTS[m.fault].bias[s] * m.faultSeverity;
      v += Math.sin(Date.now() / 1600 + s.length) * span * 0.03 + gauss(0, span * 0.02 + 0.05);
      out[s] = Math.round(Math.max(0, v) * 100) / 100;
    }
    return out;
  }

  inject(id, f) { const m = this.machines[id]; if (!m || !FAULTS[f]) return false; m.fault = f; m.faultSeverity = Math.max(m.faultSeverity, 0.25); return true; }
  repair(id) { const m = this.machines[id]; if (!m) return false; m.fault = null; m.faultSeverity = 0; m.trueHealth = 0.93; return true; }
  power(id, r) { const m = this.machines[id]; if (!m) return false; m.running = r; return true; }
}

/* ---------- AI engine (mirror of ml.py) ---------- */
const severity = (s, v) => { const c = SENSORS[s]; return Math.max(0, Math.min(1, (v - c.baseline) / (c.critical - c.baseline))); };

function healthScore(r) {
  let pen = 0, tw = 0;
  for (const [s, c] of Object.entries(SENSORS)) { pen += c.weight * severity(s, r[s] ?? c.baseline); tw += c.weight; }
  return Math.round(Math.max(0, Math.min(100, 100 * (1 - pen / tw))) * 10) / 10;
}
const band = v => v >= 80 ? "healthy" : v >= 60 ? "watch" : v >= 40 ? "warning" : "critical";

function healthSeries(m, n = 60) { return m.history.slice(-n).map(healthScore); }

function predictRUL(m) {
  const series = healthSeries(m, 60);
  const cur = series[series.length - 1] ?? 100, thr = 30, n = series.length;
  let slope = -0.05;
  if (n >= 6) {
    const xs = series.map((_, i) => i), mx = (n - 1) / 2, my = series.reduce((a, b) => a + b, 0) / n;
    let num = 0, den = 0;
    for (let i = 0; i < n; i++) { num += (xs[i] - mx) * (series[i] - my); den += (xs[i] - mx) ** 2; }
    slope = num / (den || 1e-6);
  }
  const hpt = 0.25;
  let rulH = slope < -1e-4 && cur > thr ? Math.max(0, (cur - thr) / -slope * hpt) : (cur <= thr ? 0 : 2000);
  rulH = Math.min(rulH, 5000);
  const x = (60 - cur) / 12 + Math.max(0, -slope) * 4;
  const fp = 1 / (1 + Math.exp(-x));
  return {
    current_health: Math.round(cur * 10) / 10,
    trend_per_hour: Math.round(slope / hpt * 1000) / 1000,
    rul_hours: Math.round(rulH * 10) / 10, rul_days: Math.round(rulH / 16 * 10) / 10,
    failure_probability: Math.round(Math.min(0.99, Math.max(0.01, fp)) * 100) / 100,
    confidence: Math.round(Math.min(0.95, 0.55 + n / 120) * 100) / 100,
  };
}

function median(a) { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
function detectAnomalies(m) {
  const h = m.history; if (h.length < 12) return [];
  const rec = h[h.length - 1], win = h.slice(Math.max(0, h.length - 41), h.length - 1);
  const out = [];
  for (const [s, cfg] of Object.entries(SENSORS)) {
    const ser = win.map(w => w[s]).filter(v => v != null); if (ser.length < 8) continue;
    const med = median(ser), mad = median(ser.map(v => Math.abs(v - med))) || 1e-6;
    const z = 0.6745 * (rec[s] - med) / mad;
    if (Math.abs(z) >= 3 && rec[s] > cfg.warn * 0.9)
      out.push({ sensor: s, value: rec[s], unit: cfg.unit, z_score: Math.round(z * 100) / 100, severity: Math.round(severity(s, rec[s]) * 100) / 100 });
  }
  return out.sort((a, b) => b.severity - a.severity);
}

function machineAlerts(m) {
  const reading = m.history[m.history.length - 1] || {};
  const out = [], seen = new Set();
  for (const a of detectAnomalies(m)) {
    out.push({ sensor: a.sensor, value: a.value, unit: a.unit, severity: a.severity, kind: "anomaly", z_score: a.z_score, level: a.severity >= 0.85 ? "critical" : "warning" });
    seen.add(a.sensor);
  }
  for (const [s, cfg] of Object.entries(SENSORS)) {
    const v = reading[s];
    if (v == null || seen.has(s)) continue;
    if (v >= cfg.warn) out.push({ sensor: s, value: v, unit: cfg.unit, severity: Math.round(severity(s, v) * 100) / 100, kind: "threshold", z_score: null, level: v >= cfg.critical ? "critical" : "warning" });
  }
  return out.sort((a, b) => b.severity - a.severity);
}

function energy(m) {
  const h = m.history.slice(-60); if (!h.length) return {};
  const p = h.map(x => x.power), avg = p.reduce((a, b) => a + b, 0) / p.length;
  const ideal = RATED_POWER_KW * 0.72, waste = Math.max(0, avg - ideal);
  const eff = Math.round(Math.min(100, avg ? ideal / avg * 100 : 100) * 10) / 10;
  const daily = avg * 16, monthly = daily * 26, wasteMo = waste * 16 * 26;
  return {
    avg_power_kw: Math.round(avg * 100) / 100, efficiency_pct: eff, waste_kw: Math.round(waste * 100) / 100,
    monthly_kwh: Math.round(monthly), monthly_cost_inr: Math.round(monthly * 8.5),
    potential_monthly_savings_inr: Math.round(wasteMo * 8.5), co2_kg_month: Math.round(monthly * 0.82),
  };
}

const REASONS = {
  vibration: "elevated vibration suggests mechanical imbalance, bearing wear or misalignment",
  temperature: "high temperature indicates friction, overload or cooling/lubrication issues",
  current: "abnormal current draw points to electrical overload or mechanical binding",
  sound: "acoustic emissions above normal often precede bearing or gear failure",
  power: "excess power consumption signals reduced efficiency and mechanical stress",
};
function explain(r) {
  const tw = Object.values(SENSORS).reduce((a, c) => a + c.weight, 0);
  const contribs = Object.entries(SENSORS).map(([s, c]) => {
    const sev = severity(s, r[s] ?? c.baseline);
    return { sensor: s, value: r[s] ?? c.baseline, unit: c.unit, severity: Math.round(sev * 100) / 100,
      contribution_pct: Math.round(c.weight / tw * sev * 1000) / 10,
      status: sev >= 0.85 ? "critical" : sev >= 0.55 ? "warn" : "normal" };
  }).sort((a, b) => b.contribution_pct - a.contribution_pct);
  let reasons = contribs.filter(c => c.severity >= 0.55)
    .map(c => `${c.sensor[0].toUpperCase() + c.sensor.slice(1)} at ${c.value}${c.unit} — ${REASONS[c.sensor]}`);
  if (!reasons.length) reasons = ["All sensor readings are within normal operating limits."];
  return { contributions: contribs, reasons };
}

const ACTIONS = {
  vibration: ["Inspect & rebalance rotating assembly; check bearings and mounts", "High"],
  temperature: ["Check cooling/lubrication system; reduce load until stabilised", "High"],
  current: ["Inspect electrical connections and motor windings; verify load", "Medium"],
  sound: ["Acoustic inspection of bearings/gears; schedule lubrication", "Medium"],
  power: ["Energy audit; check for mechanical drag and idle running", "Low"],
};
function recommend(m, r, rul) {
  const recs = explain(r).contributions.filter(c => c.severity >= 0.55).map(c => ({
    action: ACTIONS[c.sensor][0], driver: c.sensor,
    priority: c.severity >= 0.85 ? "Critical" : ACTIONS[c.sensor][1],
  }));
  if (rul.failure_probability >= 0.6 && !recs.length)
    recs.push({ action: "Schedule preventive inspection within the maintenance window", driver: "trend", priority: "Medium" });
  if (!recs.length) recs.push({ action: "No action required — continue routine monitoring", driver: "none", priority: "None" });
  return recs;
}

function twin(m, action) {
  const r = { ...(m.history[m.history.length - 1] || {}) };
  const before = healthScore(r), bRul = predictRUL(m), bEnergy = energy(m);
  const effects = {
    preventive_maintenance: Object.fromEntries(Object.keys(SENSORS).map(s => [s, 0.35])),
    bearing_replacement: { vibration: 0.2, sound: 0.25, temperature: 0.6 },
    lubrication: { temperature: 0.55, vibration: 0.7, sound: 0.6 },
    cooling_service: { temperature: 0.25, current: 0.7, power: 0.75 },
    electrical_service: { current: 0.3, power: 0.55, temperature: 0.7 },
    no_action: Object.fromEntries(Object.keys(SENSORS).map(s => [s, 1.0])),
  };
  const f = effects[action] || {};
  const proj = {};
  for (const [s, c] of Object.entries(SENSORS)) proj[s] = Math.round((c.baseline + ((r[s] ?? c.baseline) - c.baseline) * (f[s] ?? 1)) * 100) / 100;
  const after = healthScore(proj), gain = Math.max(0, after - before);
  const afterRul = bRul.rul_hours + gain * 22, afterFail = Math.max(0.02, bRul.failure_probability * (1 - gain / 120));
  const saved = Math.max(0, (bEnergy.avg_power_kw - proj.power)) * 16 * 26 * 8.5;
  return {
    action,
    before: { health: before, rul_hours: bRul.rul_hours, failure_probability: bRul.failure_probability, readings: r },
    after: { health: after, rul_hours: Math.round(afterRul * 10) / 10, failure_probability: Math.round(afterFail * 100) / 100, readings: proj },
    delta: { health: Math.round((after - before) * 10) / 10, rul_hours: Math.round((afterRul - bRul.rul_hours) * 10) / 10, monthly_energy_savings_inr: Math.round(saved) },
  };
}

/* ---------- LocalAPI: same shape as the REST endpoints ---------- */
const _fleet = new LocalFleet();
setInterval(() => _fleet.tick(), 2000);

function summary(m) {
  const r = m.history[m.history.length - 1] || {}; const sc = healthScore(r);
  return { id: m.id, name: m.name, type: m.type, location: m.location, running: m.running,
    health: sc, band: band(sc), fault: m.fault ? FAULTS[m.fault].label : null, runtime_hours: Math.round(m.runtime) };
}

const LocalAPI = {
  overview() {
    const machines = Object.values(_fleet.machines).map(summary);
    const en = Object.values(_fleet.machines).map(energy);
    return {
      fleet_size: machines.length,
      avg_health: Math.round(machines.reduce((a, x) => a + x.health, 0) / machines.length * 10) / 10,
      machines_at_risk: machines.filter(x => x.health < 60).length,
      active_alerts: Object.values(_fleet.machines).reduce((a, m) => a + machineAlerts(m).length, 0),
      running: machines.filter(x => x.running).length,
      energy: {
        monthly_cost_inr: Math.round(en.reduce((a, e) => a + (e.monthly_cost_inr || 0), 0)),
        potential_monthly_savings_inr: Math.round(en.reduce((a, e) => a + (e.potential_monthly_savings_inr || 0), 0)),
        co2_kg_month: Math.round(en.reduce((a, e) => a + (e.co2_kg_month || 0), 0)),
      },
      machines,
    };
  },
  machine(id) {
    const m = _fleet.machines[id]; if (!m) return null;
    const r = m.history[m.history.length - 1] || {}; const rul = predictRUL(m);
    return { ...summary(m),
      sensors: Object.fromEntries(Object.entries(SENSORS).map(([s, c]) => [s, { value: r[s], unit: c.unit, baseline: c.baseline, warn: c.warn, critical: c.critical }])),
      reading: r, prediction: rul, explanation: explain(r), anomalies: detectAnomalies(m), energy: energy(m), recommendations: recommend(m, r, rul) };
  },
  history(id, n = 60) {
    const m = _fleet.machines[id]; if (!m) return { points: [] };
    return { machine_id: id, points: m.history.slice(-n).map(h => ({ t: h.t, ...Object.fromEntries(Object.keys(SENSORS).map(s => [s, h[s]])), health: healthScore(h) })) };
  },
  alerts() {
    const out = [];
    for (const m of Object.values(_fleet.machines))
      for (const a of machineAlerts(m)) {
        const msg = a.kind === "anomaly"
          ? `${_cap(a.sensor)} anomaly on ${m.name}: ${a.value}${a.unit} (z=${a.z_score})`
          : `${_cap(a.sensor)} above safe limit on ${m.name}: ${a.value}${a.unit}`;
        out.push({ machine_id: m.id, machine_name: m.name, sensor: a.sensor, value: a.value, unit: a.unit, severity: a.severity, kind: a.kind, level: a.level, message: msg });
      }
    return out.sort((a, b) => b.severity - a.severity);
  },
  twin(id, action) { const m = _fleet.machines[id]; return m ? twin(m, action) : null; },
  inject(id, f) { return { ok: _fleet.inject(id, f) }; },
  repair(id) { return { ok: _fleet.repair(id) }; },
  power(id, r) { return { ok: _fleet.power(id, r) }; },
  meta() { return { sensors: SENSORS, faults: Object.fromEntries(Object.entries(FAULTS).map(([k, v]) => [k, v.label])),
    twin_actions: ["preventive_maintenance", "bearing_replacement", "lubrication", "cooling_service", "electrical_service", "no_action"] }; },
};

window.LocalAPI = LocalAPI;
window.MS_SENSORS = SENSORS;
