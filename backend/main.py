"""
MachineSense AI - FastAPI application
-------------------------------------
Exposes the simulated fleet and AI engine as a REST API and serves the
web dashboard. Run with:

    uvicorn main:app --reload --port 8000
    (or: python main.py)

Then open http://localhost:8000
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from simulator import Fleet, SENSORS, FAULT_PROFILES
import ml

FLEET = Fleet()

# Frontend lives one level up in ../frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Background task: advance the simulation continuously so data is live."""
    async def loop():
        while True:
            try:
                FLEET.tick(dt_hours=0.25)
            except Exception:
                # One bad tick must not silently kill the live-data stream.
                logging.exception("simulation tick failed")
            await asyncio.sleep(2.0)  # one reading every 2 seconds

    task = asyncio.create_task(loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="MachineSense AI API",
    description="Explainable Industrial Intelligence Platform for Indian Industry — Smart India Hackathon 2026",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _machine_summary(m) -> dict:
    # Score the last RUNNING reading: a stopped machine reads all zeros, which
    # would masquerade as perfect health and hide an active fault.
    reading = ml.last_running_reading(m)
    score = ml.health_score(reading) if reading else 100.0
    return {
        "id": m.id, "name": m.name, "type": m.type, "location": m.location,
        "running": m.running,
        "health": score,
        "band": ml.health_band(score),
        "fault": FAULT_PROFILES[m.fault]["label"] if m.fault else None,
        "runtime_hours": round(m.total_runtime_hours, 0),
    }


def _get(machine_id: str):
    m = FLEET.machines.get(machine_id)
    if not m:
        raise HTTPException(404, f"Machine {machine_id} not found")
    return m


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
# NOTE: handlers are async so they run on the event loop, serialized with the
# lifespan tick task — no threadpool races on the shared FLEET state.
@app.get("/api/overview")
async def overview():
    machines = [_machine_summary(m) for m in FLEET.machines.values()]
    n = len(machines)
    avg_health = round(sum(x["health"] for x in machines) / n, 1) if n else 0
    at_risk = [x for x in machines if x["health"] < 60]
    total_alerts = sum(len(ml.machine_alerts(m)) for m in FLEET.machines.values())

    # Fleet-wide energy roll-up.
    energy = [ml.energy_analysis(m) for m in FLEET.machines.values()]
    monthly_cost = sum(e.get("monthly_cost_inr", 0) for e in energy)
    potential_savings = sum(e.get("potential_monthly_savings_inr", 0) for e in energy)
    co2 = sum(e.get("co2_kg_month", 0) for e in energy)

    return {
        "fleet_size": n,
        "avg_health": avg_health,
        "machines_at_risk": len(at_risk),
        "active_alerts": total_alerts,
        "running": sum(1 for m in FLEET.machines.values() if m.running),
        "energy": {
            "monthly_cost_inr": round(monthly_cost),
            "potential_monthly_savings_inr": round(potential_savings),
            "co2_kg_month": round(co2),
        },
        "machines": machines,
    }


@app.get("/api/machines")
async def list_machines():
    return [_machine_summary(m) for m in FLEET.machines.values()]


@app.get("/api/machines/{machine_id}")
async def machine_detail(machine_id: str):
    m = _get(machine_id)
    # Live values show what the sensors read right now (zeros when stopped);
    # scoring/XAI/recommendations use the last running reading so a stopped
    # machine keeps its true diagnosis.
    reading = m.history[-1] if m.history else {}
    basis = ml.last_running_reading(m)
    rul = ml.predict_rul(m)
    return {
        **_machine_summary(m),
        "sensors": {s: {"value": reading.get(s), "unit": cfg["unit"],
                        "baseline": cfg["baseline"], "warn": cfg["warn"], "critical": cfg["critical"]}
                    for s, cfg in SENSORS.items()},
        "reading": reading,
        "prediction": rul,
        "explanation": ml.explain(basis),
        "anomalies": ml.detect_anomalies(m),
        "energy": ml.energy_analysis(m),
        "recommendations": ml.recommend(m, basis, rul),
    }


@app.get("/api/machines/{machine_id}/history")
async def machine_history(machine_id: str, n: int = Query(60, ge=1, le=240)):
    m = _get(machine_id)
    hist = list(m.history)[-n:]
    # Idle readings would score a fake 100: carry the last running health
    # forward through stopped stretches so the trend line stays honest.
    points, last_health = [], None
    for h in hist:
        if h.get("running", True):
            last_health = ml.health_score(h)
        points.append({
            "t": h.get("t"),
            **{s: h.get(s) for s in SENSORS},
            "health": last_health if last_health is not None else ml.health_score(h),
        })
    return {"machine_id": machine_id, "points": points}


@app.get("/api/alerts")
async def alerts():
    out = []
    for m in FLEET.machines.values():
        for a in ml.machine_alerts(m):
            if a["kind"] == "anomaly":
                msg = (f"{a['sensor'].capitalize()} anomaly on {m.name}: "
                       f"{a['value']}{a['unit']} (z={a['z_score']})")
            else:
                msg = (f"{a['sensor'].capitalize()} above safe limit on {m.name}: "
                       f"{a['value']}{a['unit']}")
            out.append({
                "machine_id": m.id, "machine_name": m.name,
                "sensor": a["sensor"], "value": a["value"], "unit": a["unit"],
                "severity": a["severity"], "kind": a["kind"], "level": a["level"],
                "message": msg,
            })
    out.sort(key=lambda x: x["severity"], reverse=True)
    return out


class TwinRequest(BaseModel):
    action: str


@app.post("/api/machines/{machine_id}/twin")
async def run_twin(machine_id: str, req: TwinRequest):
    m = _get(machine_id)
    if req.action not in ml.TWIN_EFFECTS:
        raise HTTPException(400, f"Unknown twin action {req.action!r}. Valid: {ml.TWIN_ACTIONS}")
    return ml.digital_twin(m, req.action)


class FaultRequest(BaseModel):
    fault: str


@app.post("/api/machines/{machine_id}/inject-fault")
async def inject_fault(machine_id: str, req: FaultRequest):
    _get(machine_id)  # 404 for an unknown machine, like every sibling endpoint
    if req.fault not in FAULT_PROFILES:
        raise HTTPException(400, f"Unknown fault type {req.fault!r}. Valid: {list(FAULT_PROFILES)}")
    FLEET.inject_fault(machine_id, req.fault)
    return {"ok": True, "machine_id": machine_id, "fault": req.fault}


@app.post("/api/machines/{machine_id}/repair")
async def repair(machine_id: str):
    if not FLEET.repair(machine_id):
        raise HTTPException(404, "Machine not found")
    return {"ok": True, "machine_id": machine_id}


class RunRequest(BaseModel):
    running: bool


@app.post("/api/machines/{machine_id}/power")
async def set_power(machine_id: str, req: RunRequest):
    if not FLEET.set_running(machine_id, req.running):
        raise HTTPException(404, "Machine not found")
    return {"ok": True, "machine_id": machine_id, "running": req.running}


@app.get("/api/meta")
async def meta():
    return {
        "sensors": SENSORS,
        "faults": {k: v["label"] for k, v in FAULT_PROFILES.items()},
        # Single source of truth: whatever the twin engine actually models.
        "twin_actions": ml.TWIN_ACTIONS,
    }


# ---------------------------------------------------------------------------
# Serve the frontend (mounted last so /api/* takes precedence)
# ---------------------------------------------------------------------------
if os.path.isdir(FRONTEND_DIR):
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # Bind localhost like run.bat/run.sh do — the API has wide-open CORS and
    # should not be exposed on every interface by default.
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
