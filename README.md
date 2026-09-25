# MachineSense AI

**Explainable Industrial Intelligence Platform for Indian Industry**
*Predictive Maintenance · Digital Twin Simulation · Energy Optimization*
*Smart India Hackathon 2026 · Software Edition*

**Built by Saatwik Sairaam Vasamsetti** · [github.com/saatwik-1157](https://github.com/saatwik-1157)

MachineSense AI is an Industry 4.0 platform that combines **IoT sensors**, **Explainable AI**,
predictive maintenance, energy optimization and **digital-twin simulation** to help Indian
industrial units — from small workshops to large plants — reduce downtime, maintenance cost
and energy consumption, making advanced industrial intelligence affordable and accessible.

This repository contains a **fully working software prototype**: a FastAPI service
(`apps/api`) that simulates a fleet of six industrial machines and runs the analytics
engine, plus a real-time web dashboard (`apps/web`) that the same server hosts.

---

## What it does

| Capability | Description |
|---|---|
| **Real-time Monitoring** | Live IoT telemetry — vibration, temperature, current, sound, power |
| **Machine Health Score** | A single 0–100 score per machine from weighted, normalised sensor data |
| **Predictive Maintenance** | Remaining-Useful-Life (RUL) and failure-probability forecasts from live trends |
| **Explainable AI** | Every score is broken down by sensor with plain-language root-cause reasoning |
| **Digital Twin** | "What-if" simulation of a maintenance action *before* touching the real machine |
| **Energy Optimization** | Efficiency, waste, recoverable cost and CO₂ across the fleet |
| **Smart Alerts** | Robust anomaly detection (MAD z-score) + threshold-breach alerting |

The dashboard has six views: **Fleet Overview**, **Machine Analytics**, **Digital Twin
Simulator**, **Energy Optimization**, **Alerts**, and **About**. Health gauges, live telemetry
charts, the twin before/after comparison and energy analytics are all rendered client-side
with zero external dependencies.

---

## Architecture

```
  Browser
  ┌──────────────────────────────┐
  │ Dashboard  (apps/web)        │   vanilla HTML/CSS/JS, polls every 2.5 s
  │  app.js ── fetch /api/* ─────┼──────────────┐
  │  simulator.js (fallback) ◄───┼── if the API │ is unreachable
  └──────────────────────────────┘              │
                                                ▼
  FastAPI + Uvicorn  (apps/api/main.py)   127.0.0.1:8000
  ├── /api/*  REST routes
  ├── /       static files from apps/web
  └── background task: Fleet.tick() every 2 s
            │                         │
            ▼                         ▼
  simulator.py                  ml.py
  6 simulated machines,         health score, MAD anomalies, RUL,
  sensor streams, faults        failure risk, energy, XAI, digital twin
            │
            ▼
  In-memory state only (last 240 readings per machine)
```

- **There is no database.** All fleet state lives in memory in the API process and resets
  when the server restarts.
- The "AI engine" is transparent, rule-based analytics (weighted scoring, robust statistics,
  linear trend extrapolation) written in plain Python — there is no trained ML model file.
- The target product vision (ESP32 sensors → edge gateway → cloud → AI engine → digital twin →
  recommendations → dashboard) is described in [`docs/ONE_PAGER.md`](docs/ONE_PAGER.md); in
  this prototype the simulator stands in for the real sensor stream.

**Design note:** the dashboard and the API implement the *same* analytics (health scoring,
anomaly detection, RUL, digital twin) in JavaScript and Python. This keeps the demo reliable:
it looks and behaves identically whether the FastAPI server is running or not.

---

## Project structure

```
machinesense-ai/
├── apps/
│   ├── api/                   # Python service (FastAPI)
│   │   ├── main.py            # FastAPI app, REST API, serves apps/web
│   │   ├── simulator.py       # Industrial machine & IoT sensor simulator
│   │   ├── ml.py              # Analytics: health, anomalies, RUL, energy, twin, XAI
│   │   ├── requirements.txt
│   │   └── README.md
│   └── web/                   # Browser dashboard (no build step)
│       ├── index.html         # Dashboard shell
│       ├── styles.css         # Dark industrial theme
│       ├── charts.js          # Dependency-free canvas charts (line, gauge, donut)
│       ├── simulator.js       # In-browser fallback simulator (mirrors the API)
│       ├── app.js             # SPA: routing, API layer, all views
│       └── README.md
├── docs/
│   ├── MachineSenseAI_Pitch_Deck.pptx
│   ├── build_deck.py          # Regenerates the pitch deck (python-pptx)
│   ├── MachineSenseAISIHdemosubtitled.mp4
│   ├── ONE_PAGER.md
│   ├── SIH2026_project_mapping.md
│   └── SIH2026_Theme_Decision.pdf
├── .claude/launch.json        # Dev-server config for Claude Code preview
├── run.bat                    # One-click launcher (Windows)
├── run.sh                     # One-click launcher (macOS / Linux)
└── README.md
```

---

## Technology stack

| Layer | What is actually used |
|---|---|
| API | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| Analytics / simulation | Python standard library only (`statistics`, `math`, `random`) |
| Dashboard | Plain HTML, CSS and JavaScript; canvas charts; no framework, no build step |
| Storage | None (in-memory) |
| Pitch deck | `python-pptx` (only needed to rebuild the deck, not to run the app) |

**Hardware (target):** ESP32 + vibration / current / sound / temperature sensors.
**Production target (not in this repo):** React · PostgreSQL · Docker.

---

## Getting started

Requires **Python 3.10 or newer** on your `PATH`.

### Option A — Full stack (recommended)

The launchers install the API dependencies and start the server, which also serves the
dashboard.

**Windows**

```bat
run.bat
```

**macOS / Linux**

```bash
./run.sh
```

**Manually** (from the repository root; a virtual environment is recommended):

```bash
# Windows:      python -m venv .venv  &&  .venv\Scripts\activate
# macOS/Linux:  python3 -m venv .venv &&  source .venv/bin/activate
pip install -r apps/api/requirements.txt
python -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8000
# or: python apps/api/main.py
```

Then open **http://localhost:8000**. The sidebar shows **"Live · FastAPI backend"**.
Add `--reload` to the uvicorn command during development.

### Option B — Dashboard only (no install)

The dashboard ships with an in-browser fallback simulator, so it works without the API:
open `apps/web/index.html` directly in a browser. The sidebar shows **"Demo mode ·
in-browser simulation"** and all six views remain fully functional — the data is generated
in JavaScript instead of Python.

### Configuration

The app reads no environment variables, so there is no `.env` file. Host and port are set
on the uvicorn command line (the launchers use `127.0.0.1:8000`).

---

## API reference

Base URL: `http://localhost:8000`. Machine ids are `M-001` … `M-006`.

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/overview` | Fleet KPIs, energy roll-up and per-machine summaries |
| `GET`  | `/api/machines` | List of machine summaries |
| `GET`  | `/api/machines/{id}` | Full detail: sensors, prediction, XAI, anomalies, energy, recommendations |
| `GET`  | `/api/machines/{id}/history?n=60` | Time-series telemetry + health (`n` = 1–240) |
| `GET`  | `/api/alerts` | Active alerts (anomalies + threshold breaches), most severe first |
| `GET`  | `/api/meta` | Sensor config, fault types, twin actions |
| `POST` | `/api/machines/{id}/twin` | Digital-twin what-if — body: `{"action": "bearing_replacement"}` |
| `POST` | `/api/machines/{id}/inject-fault` | Demo: inject a fault — body: `{"fault": "overheating"}` |
| `POST` | `/api/machines/{id}/repair` | Demo: simulate a completed repair (no body) |
| `POST` | `/api/machines/{id}/power` | Start/stop a machine — body: `{"running": false}` |

- Twin actions: `preventive_maintenance`, `bearing_replacement`, `lubrication`,
  `cooling_service`, `electrical_service`, `no_action`.
- Fault types: `bearing_wear`, `overheating`, `electrical_overload`, `misalignment`,
  `lubrication_loss`.
- Unknown machine → `404`; unknown action or fault → `400` listing the valid values.

Interactive API docs (Swagger UI) are auto-generated at **http://localhost:8000/docs**.

---

## How the analytics engine works

- **Health Score** — each sensor's deviation from its baseline toward its critical threshold
  is normalised to `[0,1]`, weighted by importance, and combined into a 0–100 score.
- **Anomaly detection** — a robust **median-absolute-deviation z-score** flags sudden
  deviations against each machine's own recent history (resistant to outliers).
- **RUL / failure risk** — least-squares slope of the recent health trend is extrapolated to
  a failure threshold; failure probability is a logistic function of health + degradation speed.
- **Energy** — average power draw vs. the healthy-machine baseline yields efficiency, monthly
  cost, recoverable waste and CO₂ (India grid factor ≈ 0.82 kg/kWh, tariff ≈ ₹8.5/kWh) — a
  pristine machine shows ~zero waste, so savings reflect real degradation.
- **Explainable AI** — the health penalty is attributed back to each sensor with a
  plain-language reason, so operators see *why*, not just a number.
- **Digital Twin** — models each maintenance action as a reduction of sensor severities and
  projects the resulting health, RUL, failure risk and energy savings — before any action.

---

## Testing

There is **no automated test suite** in this repository yet. A quick manual smoke test:

```bash
python -m uvicorn main:app --app-dir apps/api --port 8000 &
curl http://127.0.0.1:8000/api/overview
curl -X POST http://127.0.0.1:8000/api/machines/M-001/twin \
     -H "Content-Type: application/json" -d '{"action": "bearing_replacement"}'
```

Then open the dashboard and check that the sidebar says "Live · FastAPI backend".

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python` is not recognised (Windows) | Install Python 3.10+ from python.org and tick "Add python.exe to PATH". |
| `./run.sh: Permission denied` | `chmod +x run.sh`, or run `bash run.sh`. |
| `Error loading ASGI app. Could not import module "main"` | Run from the repo root, or pass `--app-dir apps/api`. |
| `address already in use` on port 8000 | Stop the other process or start with a different `--port`, e.g. `--port 8001`. |
| Dashboard says "Demo mode" while the server runs | You opened `index.html` as a file. Use `http://localhost:8000` instead. |
| `/` returns 404 but `/api/*` works | The server could not find `apps/web`; it logs a "Dashboard not found" warning. Keep `apps/api` and `apps/web` side by side. |
| Data resets after a restart | Expected — there is no database; state is in memory. |

---

## Project snapshot

- **Domain:** Industry 4.0 · AI · IoT · Digital Twin · Predictive Maintenance
- **Event:** Smart India Hackathon 2026 (Software)
- **Status:** Working full-stack prototype — live simulated fleet, real analytics
- **Impact:** Predictive maintenance typically cuts downtime ~30%; energy optimization saves 10–20%

See [`docs/ONE_PAGER.md`](docs/ONE_PAGER.md) and the pitch deck in `docs/` for the full story.

---

*Built for Smart India Hackathon 2026.*
