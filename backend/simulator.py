"""
MachineSense AI - Industrial Machine & Sensor Simulator
--------------------------------------------------------
Simulates a fleet of industrial machines and their IoT sensor streams
(vibration, temperature, current, sound, power). Each machine has an
internal "true health" that degrades over time and can be pushed into fault
states for live demos. Sensor readings are derived from the true health plus
realistic noise, so the AI engine (ml.py) has something meaningful to analyse.

No external dependencies - pure Python standard library. This keeps the demo
reliable on machines without a data-science stack installed.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Deque, Dict, List
from collections import deque


# ---------------------------------------------------------------------------
# Sensor definitions: healthy baseline, warning band and critical thresholds.
# Values are representative of small/medium industrial equipment.
# ---------------------------------------------------------------------------
SENSORS = {
    "vibration": {"unit": "mm/s", "baseline": 2.0, "warn": 4.5, "critical": 7.1, "weight": 0.30},
    "temperature": {"unit": "°C", "baseline": 55.0, "warn": 75.0, "critical": 90.0, "weight": 0.25},
    "current": {"unit": "A", "baseline": 12.0, "warn": 16.0, "critical": 20.0, "weight": 0.15},
    "sound": {"unit": "dB", "baseline": 72.0, "warn": 85.0, "critical": 95.0, "weight": 0.15},
    "power": {"unit": "kW", "baseline": 7.5, "warn": 10.5, "critical": 13.0, "weight": 0.15},
}

RATED_POWER_KW = 9.0  # nameplate rating used for energy-efficiency maths


@dataclass
class Machine:
    """A single industrial asset with an evolving health state."""

    id: str
    name: str
    type: str
    location: str
    # true_health: 1.0 = pristine, 0.0 = failed. Hidden from the UI; the AI
    # only ever sees the sensor readings derived from it.
    true_health: float = 1.0
    # per-tick degradation rate (baseline wear)
    degradation: float = 0.00035
    # active fault: None or one of the FAULT_PROFILES keys
    fault: str | None = None
    fault_severity: float = 0.0  # 0..1, how far the fault has progressed
    running: bool = True
    # rolling history of readings for trend analysis / charts
    history: Deque[dict] = field(default_factory=lambda: deque(maxlen=240))
    installed_days: int = 0
    total_runtime_hours: float = 0.0

    def snapshot_true_health(self) -> float:
        return max(0.0, min(1.0, self.true_health))


# Fault profiles bias particular sensors so failures look realistic and the
# explainable-AI layer can attribute them to a plausible root cause.
FAULT_PROFILES = {
    "bearing_wear": {"label": "Bearing Wear", "bias": {"vibration": 3.4, "sound": 8.0, "temperature": 6.0}},
    "overheating": {"label": "Overheating", "bias": {"temperature": 22.0, "current": 3.0, "power": 2.2}},
    "electrical_overload": {"label": "Electrical Overload", "bias": {"current": 6.0, "power": 4.0, "temperature": 5.0}},
    "misalignment": {"label": "Shaft Misalignment", "bias": {"vibration": 2.6, "sound": 5.0}},
    "lubrication_loss": {"label": "Lubrication Loss", "bias": {"temperature": 9.0, "vibration": 1.8, "sound": 4.0}},
}


class Fleet:
    """Holds all machines and advances the simulation over time."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self._sim_hours = 0.0
        self.machines: Dict[str, Machine] = {}
        self._build_fleet()
        # Pre-seed history on healthy machines so charts are populated at load.
        # Warm-up uses the same 0.25 h tick as live operation so trend maths
        # (RUL slope, hours-per-tick) sees a uniform time base.
        for _ in range(120):
            self.tick()
        # Apply demo faults AFTER warm-up so they start fresh, not flatlined.
        self._seed_faults()
        # Run a few more ticks so the seeded faults are reflected in the
        # latest readings immediately (no healthy-looking cold-start window).
        for _ in range(16):
            self.tick()

    def _build_fleet(self):
        specs = [
            ("M-001", "CNC Milling Machine", "CNC", "Shop Floor A", 0.00040, 620),
            ("M-002", "Air Compressor", "Compressor", "Utility Room", 0.00055, 810),
            ("M-003", "Injection Moulder", "Moulding", "Shop Floor B", 0.00048, 430),
            ("M-004", "Conveyor Motor", "Motor", "Packaging Line", 0.00030, 350),
            ("M-005", "Hydraulic Press", "Press", "Shop Floor A", 0.00060, 900),
            ("M-006", "Cooling Pump", "Pump", "Utility Room", 0.00038, 540),
        ]
        for mid, name, mtype, loc, degr, days in specs:
            m = Machine(
                id=mid, name=name, type=mtype, location=loc,
                degradation=degr,
                true_health=self.rng.uniform(0.80, 0.99),
                installed_days=days,
                total_runtime_hours=days * self.rng.uniform(9, 15),
            )
            self.machines[mid] = m

    def _seed_faults(self):
        # Give the demo an interesting spread: one critical, one developing.
        m2 = self.machines["M-002"]
        m2.fault = "bearing_wear"
        m2.fault_severity = 0.5
        m2.true_health = 0.5
        m5 = self.machines["M-005"]
        m5.fault = "overheating"
        m5.fault_severity = 0.28
        m5.true_health = 0.68

    # ------------------------------------------------------------------
    # Simulation step
    # ------------------------------------------------------------------
    def tick(self, dt_hours: float = 0.25):
        """Advance every running machine by dt_hours and record a reading."""
        self._sim_hours += dt_hours
        for m in self.machines.values():
            if not m.running:
                self._record(m, running=False)
                continue

            m.total_runtime_hours += dt_hours

            # Baseline wear.
            wear = m.degradation
            # Faults accelerate wear as they worsen (kept gentle so a live
            # demo degrades gradually instead of flatlining in seconds).
            if m.fault:
                m.fault_severity = min(1.0, m.fault_severity + self.rng.uniform(0.0004, 0.0018))
                wear += m.fault_severity * 0.0012
            m.true_health = max(0.0, m.true_health - wear)

            self._record(m, running=True)

    def _record(self, m: Machine, running: bool):
        reading = self._read_sensors(m, running)
        # Simulated elapsed hours: monotone and uniform even during the fast
        # warm-up loop (wall-clock would stamp all warm-up points identically).
        reading["t"] = round(self._sim_hours, 2)
        reading["running"] = running
        m.history.append(reading)

    def _read_sensors(self, m: Machine, running: bool) -> dict:
        """Derive noisy sensor values from the machine's hidden true health."""
        out = {}
        # Health deficit drives readings away from baseline toward critical.
        deficit = 1.0 - m.snapshot_true_health()  # 0 healthy .. 1 failed
        phase = time.time() * 0.6  # for gentle oscillation

        for s, cfg in SENSORS.items():
            if not running:
                out[s] = 0.0 if s in ("vibration", "current", "sound", "power") else 22.0
                continue

            base = cfg["baseline"]
            span = cfg["critical"] - base
            # Degradation pushes readings up proportionally.
            val = base + span * deficit * 0.85
            # Fault-specific bias.
            if m.fault:
                bias = FAULT_PROFILES[m.fault]["bias"].get(s, 0.0)
                val += bias * m.fault_severity
            # Realistic noise + slow oscillation.
            val += math.sin(phase + hash(s) % 7) * (span * 0.03)
            val += self.rng.gauss(0, span * 0.02 + 0.05)
            out[s] = round(max(0.0, val), 2)
        return out

    # ------------------------------------------------------------------
    # Demo controls
    # ------------------------------------------------------------------
    def inject_fault(self, machine_id: str, fault: str) -> bool:
        m = self.machines.get(machine_id)
        if not m or fault not in FAULT_PROFILES:
            return False
        m.fault = fault
        m.fault_severity = max(m.fault_severity, 0.25)
        return True

    def repair(self, machine_id: str) -> bool:
        """Simulate a completed maintenance action (used by the digital twin)."""
        m = self.machines.get(machine_id)
        if not m:
            return False
        m.fault = None
        m.fault_severity = 0.0
        # Partial restore (+0.35), never below a solid 0.90 nor a suspicious 1.0.
        m.true_health = min(0.99, max(0.90, m.true_health + 0.35))
        return True

    def set_running(self, machine_id: str, running: bool) -> bool:
        m = self.machines.get(machine_id)
        if not m:
            return False
        m.running = running
        return True
