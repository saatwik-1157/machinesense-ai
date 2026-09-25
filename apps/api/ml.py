"""
MachineSense AI - AI / Analytics Engine
---------------------------------------
Turns raw sensor readings into decisions:

  * Machine Health Score (0-100)  - weighted, normalised sensor deviation
  * Anomaly detection             - robust z-score vs. recent baseline
  * Remaining Useful Life (RUL)   - linear degradation extrapolation
  * Failure probability           - logistic function of health + trend
  * Energy analytics              - efficiency, waste, savings estimate
  * Explainable AI                - per-sensor contribution + plain-English "why"
  * Recommendations               - prioritised maintenance actions
  * Digital Twin                  - "what-if" projection of an action's effect

Pure standard-library statistics so it runs anywhere Python does.
"""

from __future__ import annotations

import statistics
from typing import Dict, List

from simulator import SENSORS, FAULT_PROFILES, Machine


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------
def last_running_reading(machine: Machine) -> dict:
    """Latest reading taken while the machine was running (idle readings are
    all-zero and would masquerade as perfect health)."""
    for h in reversed(machine.history):
        if h.get("running", True):
            return h
    return machine.history[-1] if machine.history else {}


def _sensor_severity(sensor: str, value: float) -> float:
    """0.0 = healthy baseline, 1.0 = at/over critical threshold."""
    cfg = SENSORS[sensor]
    base, crit = cfg["baseline"], cfg["critical"]
    if crit <= base:
        return 0.0
    return max(0.0, min(1.0, (value - base) / (crit - base)))


def health_score(reading: dict) -> float:
    """Weighted health score in [0, 100]. 100 = perfect health."""
    penalty = 0.0
    total_w = 0.0
    for s, cfg in SENSORS.items():
        w = cfg["weight"]
        penalty += w * _sensor_severity(s, reading.get(s, cfg["baseline"]))
        total_w += w
    score = 100.0 * (1.0 - penalty / total_w)
    return round(max(0.0, min(100.0, score)), 1)


def health_band(score: float) -> str:
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "watch"
    if score >= 40:
        return "warning"
    return "critical"


# ---------------------------------------------------------------------------
# Anomaly detection (robust z-score against the machine's recent history)
# ---------------------------------------------------------------------------
def detect_anomalies(machine: Machine) -> List[dict]:
    # Idle readings are all-zero: exclude them from the baseline window, and
    # don't run the test at all while the machine is stopped.
    hist = [h for h in machine.history if h.get("running", True)]
    if len(hist) < 12:
        return []
    recent = machine.history[-1] if machine.history else {}
    if not recent.get("running", True):
        return []
    window = hist[-40:-1] if len(hist) > 41 else hist[:-1]
    anomalies = []
    for s, cfg in SENSORS.items():
        series = [h[s] for h in window if s in h]
        if len(series) < 8:
            continue
        med = statistics.median(series)
        # Median absolute deviation -> robust to outliers. Floor the MAD at a
        # small fraction of the baseline so a near-constant window can't
        # produce astronomical z-scores.
        mad = max(statistics.median([abs(x - med) for x in series]), 0.02 * cfg["baseline"])
        z = 0.6745 * (recent[s] - med) / mad
        if abs(z) >= 3.0 and recent[s] > cfg["warn"] * 0.9:
            anomalies.append({
                "sensor": s,
                "value": recent[s],
                "unit": cfg["unit"],
                "z_score": round(z, 2),
                "severity": round(_sensor_severity(s, recent[s]), 2),
            })
    anomalies.sort(key=lambda a: a["severity"], reverse=True)
    return anomalies


def machine_alerts(machine: Machine) -> List[dict]:
    """
    Combined alert stream for a machine: statistical anomalies (sudden
    deviations) PLUS sustained threshold breaches (a sensor parked above its
    warning limit). De-duplicated per sensor, most severe first.
    """
    reading = machine.history[-1] if machine.history else {}
    alerts: List[dict] = []
    seen = set()

    for a in detect_anomalies(machine):
        alerts.append({
            "sensor": a["sensor"], "value": a["value"], "unit": a["unit"],
            "severity": a["severity"], "kind": "anomaly", "z_score": a["z_score"],
            "level": "critical" if a["severity"] >= 0.85 else "warning",
        })
        seen.add(a["sensor"])

    for s, cfg in SENSORS.items():
        v = reading.get(s)
        if v is None or s in seen:
            continue
        if v >= cfg["warn"]:
            sev = _sensor_severity(s, v)
            alerts.append({
                "sensor": s, "value": v, "unit": cfg["unit"],
                "severity": round(sev, 2), "kind": "threshold", "z_score": None,
                "level": "critical" if v >= cfg["critical"] else "warning",
            })

    alerts.sort(key=lambda a: a["severity"], reverse=True)
    return alerts


# ---------------------------------------------------------------------------
# Remaining Useful Life + failure probability
# ---------------------------------------------------------------------------
def _health_series(machine: Machine, n: int = 60) -> List[float]:
    # Trend only over running readings; idle all-zero readings score 100 and
    # would corrupt the degradation slope.
    running = [h for h in machine.history if h.get("running", True)]
    return [health_score(h) for h in running[-n:]]


def predict_rul(machine: Machine) -> dict:
    """
    Estimate Remaining Useful Life by extrapolating the health trend to a
    failure threshold (health = 30). Returns hours + a human-readable window.
    """
    series = _health_series(machine, 60)
    current = series[-1] if series else 100.0
    threshold = 30.0

    # Slope of health per tick via simple least-squares on the recent window.
    n = len(series)
    if n >= 6:
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(series) / n
        denom = sum((x - mean_x) ** 2 for x in xs) or 1e-6
        slope = sum((xs[i] - mean_x) * (series[i] - mean_y) for i in range(n)) / denom
    else:
        slope = -0.05

    # Each tick ~= 0.25 simulated hours (see simulator.tick default).
    hours_per_tick = 0.25
    if slope < -1e-4 and current > threshold:
        ticks_to_fail = (current - threshold) / (-slope)
        rul_hours = max(0.0, ticks_to_fail * hours_per_tick)
    elif current <= threshold:
        rul_hours = 0.0
    else:
        rul_hours = 2000.0  # effectively stable

    rul_hours = min(rul_hours, 5000.0)
    rul_days = rul_hours / 16.0  # ~16 operating hours/day (2 shifts)

    # Failure probability: logistic on health + degradation speed.
    trend_penalty = max(0.0, -slope) * 4.0
    x = (60.0 - current) / 12.0 + trend_penalty
    fail_prob = 1.0 / (1.0 + pow(2.718281828, -x))

    return {
        "current_health": round(current, 1),
        "trend_per_hour": round(slope / hours_per_tick, 3),
        "rul_hours": round(rul_hours, 1),
        "rul_days": round(rul_days, 1),
        "failure_probability": round(min(0.99, max(0.01, fail_prob)), 2),
        "confidence": round(min(0.95, 0.55 + n / 120.0), 2),
    }


# ---------------------------------------------------------------------------
# Energy analytics
# ---------------------------------------------------------------------------
def energy_analysis(machine: Machine, tariff_inr_per_kwh: float = 8.5) -> dict:
    hist = list(machine.history)[-60:]
    if not hist:
        return {}
    powers = [h["power"] for h in hist if "power" in h]
    avg_power = sum(powers) / len(powers) if powers else 0.0

    # Ideal power draw = the healthy-machine baseline, so a pristine machine
    # shows ~zero waste and savings reflect real degradation only.
    ideal = SENSORS["power"]["baseline"]
    waste_kw = max(0.0, avg_power - ideal)
    efficiency = round(min(100.0, (ideal / avg_power * 100.0) if avg_power else 100.0), 1)

    # Project to daily / monthly figures (16 operating hours/day, 26 days/mo).
    daily_kwh = avg_power * 16.0
    monthly_kwh = daily_kwh * 26.0
    waste_kwh_month = waste_kw * 16.0 * 26.0
    monthly_cost = round(monthly_kwh * tariff_inr_per_kwh, 0)
    monthly_savings = round(waste_kwh_month * tariff_inr_per_kwh, 0)

    return {
        "avg_power_kw": round(avg_power, 2),
        "efficiency_pct": efficiency,
        "waste_kw": round(waste_kw, 2),
        "monthly_kwh": round(monthly_kwh, 0),
        "monthly_cost_inr": monthly_cost,
        "potential_monthly_savings_inr": monthly_savings,
        "co2_kg_month": round(monthly_kwh * 0.82, 0),  # ~0.82 kg CO2 / kWh (India grid)
    }


# ---------------------------------------------------------------------------
# Explainable AI - why is the score what it is?
# ---------------------------------------------------------------------------
_SENSOR_REASONS = {
    "vibration": "elevated vibration suggests mechanical imbalance, bearing wear or misalignment",
    "temperature": "high temperature indicates friction, overload or cooling/lubrication issues",
    "current": "abnormal current draw points to electrical overload or mechanical binding",
    "sound": "acoustic emissions above normal often precede bearing or gear failure",
    "power": "excess power consumption signals reduced efficiency and mechanical stress",
}


def explain(reading: dict) -> dict:
    """Attribute the health penalty to each sensor and give plain-English reasons."""
    contribs = []
    total_w = sum(c["weight"] for c in SENSORS.values())
    for s, cfg in SENSORS.items():
        sev = _sensor_severity(s, reading.get(s, cfg["baseline"]))
        contribution = (cfg["weight"] / total_w) * sev
        contribs.append({
            "sensor": s,
            "value": reading.get(s, cfg["baseline"]),
            "unit": cfg["unit"],
            "severity": round(sev, 2),
            "contribution_pct": round(contribution * 100, 1),
            "status": "critical" if sev >= 0.85 else "warn" if sev >= 0.55 else "normal",
        })
    contribs.sort(key=lambda c: c["contribution_pct"], reverse=True)

    reasons = [
        f"{c['sensor'].capitalize()} at {c['value']}{c['unit']} — {_SENSOR_REASONS[c['sensor']]}"
        for c in contribs if c["severity"] >= 0.55
    ]
    if not reasons:
        reasons = ["All sensor readings are within normal operating limits."]
    return {"contributions": contribs, "reasons": reasons}


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
_ACTION_LIBRARY = {
    "vibration": ("Inspect & rebalance rotating assembly; check bearings and mounts", "High"),
    "temperature": ("Check cooling/lubrication system; reduce load until stabilised", "High"),
    "current": ("Inspect electrical connections and motor windings; verify load", "Medium"),
    "sound": ("Acoustic inspection of bearings/gears; schedule lubrication", "Medium"),
    "power": ("Energy audit; check for mechanical drag and idle running", "Low"),
}


def recommend(machine: Machine, reading: dict, rul: dict) -> List[dict]:
    exp = explain(reading)
    recs = []
    for c in exp["contributions"]:
        if c["severity"] >= 0.55:
            action, base_prio = _ACTION_LIBRARY[c["sensor"]]
            prio = "Critical" if c["severity"] >= 0.85 else base_prio
            recs.append({
                "action": action,
                "driver": c["sensor"],
                "priority": prio,
            })
    if rul["failure_probability"] >= 0.6 and not recs:
        recs.append({
            "action": "Schedule preventive inspection within the maintenance window",
            "driver": "trend",
            "priority": "Medium",
        })
    if not recs:
        recs.append({
            "action": "No action required — continue routine monitoring",
            "driver": "none",
            "priority": "None",
        })
    return recs


# ---------------------------------------------------------------------------
# Digital Twin - simulate the effect of a maintenance action before doing it
# ---------------------------------------------------------------------------
# Each action is modelled as a multiplicative reduction of sensor severities.
TWIN_EFFECTS = {
    "preventive_maintenance": {s: 0.35 for s in SENSORS},
    "bearing_replacement": {"vibration": 0.2, "sound": 0.25, "temperature": 0.6},
    "lubrication": {"temperature": 0.55, "vibration": 0.7, "sound": 0.6},
    "cooling_service": {"temperature": 0.25, "current": 0.7, "power": 0.75},
    "electrical_service": {"current": 0.3, "power": 0.55, "temperature": 0.7},
    "no_action": {s: 1.0 for s in SENSORS},
}
TWIN_ACTIONS = list(TWIN_EFFECTS)


def digital_twin(machine: Machine, action: str) -> dict:
    """
    Project the machine's health, RUL and energy AFTER a chosen action, without
    touching the real asset. Lets operators validate decisions first.

    Raises ValueError for an action not in TWIN_EFFECTS.
    """
    if action not in TWIN_EFFECTS:
        raise ValueError(f"Unknown twin action: {action!r}")

    reading = dict(last_running_reading(machine)) or {s: SENSORS[s]["baseline"] for s in SENSORS}
    reading.pop("running", None)
    before_score = health_score(reading)
    before_rul = predict_rul(machine)
    before_energy = energy_analysis(machine)

    factor = TWIN_EFFECTS[action]

    projected = {}
    for s, cfg in SENSORS.items():
        base = cfg["baseline"]
        val = reading.get(s, base)
        f = factor.get(s, 1.0)
        projected[s] = round(base + (val - base) * f, 2)

    after_score = health_score(projected)
    # Approximate RUL uplift proportional to health gain.
    gain = max(0.0, after_score - before_score)
    after_rul_hours = before_rul["rul_hours"] + gain * 22.0
    after_fail = max(0.02, before_rul["failure_probability"] * (1 - gain / 120.0))

    after_power = projected["power"]
    energy_saved_month = max(0.0, (before_energy.get("avg_power_kw", after_power) - after_power)) * 16 * 26 * 8.5

    return {
        "action": action,
        "before": {
            "health": before_score,
            "rul_hours": before_rul["rul_hours"],
            "failure_probability": before_rul["failure_probability"],
            "readings": reading,
        },
        "after": {
            "health": after_score,
            "rul_hours": round(after_rul_hours, 1),
            "failure_probability": round(after_fail, 2),
            "readings": projected,
        },
        "delta": {
            "health": round(after_score - before_score, 1),
            "rul_hours": round(after_rul_hours - before_rul["rul_hours"], 1),
            "monthly_energy_savings_inr": round(energy_saved_month, 0),
        },
    }
