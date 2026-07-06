# MachineSense AI

**Explainable Industrial Intelligence Platform for MSMEs**
*Predictive Maintenance · Digital Twin Simulation · Energy Optimization*

MachineSense AI is an Industry 4.0 platform that combines **IoT sensors**, **Explainable AI**,
predictive maintenance, energy optimization and **digital-twin simulation** to help
Micro, Small & Medium Enterprises (MSMEs) reduce downtime, maintenance cost and energy
consumption — making advanced industrial intelligence affordable and accessible.

This repository contains a **fully working software prototype**: a FastAPI backend that
simulates a fleet of industrial machines and runs the AI/analytics engine, plus a polished
real-time web dashboard.

---

## ✨ What it does

| Capability | Description |
|---|---|
| **Real-time Monitoring** | Live IoT telemetry — vibration, temperature, current, sound, power |
| **Machine Health Score** | A single 0–100 score per machine from weighted, normalised sensor data |
| **Predictive Maintenance** | Remaining-Useful-Life (RUL) and failure-probability forecasts from live trends |
| **Explainable AI** | Every score is broken down by sensor with plain-language root-cause reasoning |
| **Digital Twin** | "What-if" simulation of a maintenance action *before* touching the real machine |
| **Energy Optimization** | Efficiency, waste, recoverable cost and CO₂ across the fleet |
| **Smart Alerts** | Robust anomaly detection (MAD z-score) + threshold-breach alerting |

---

## 🖥️ Screenshots

The dashboard has six views: **Fleet Overview**, **Machine Analytics**, **Digital Twin
Simulator**, **Energy Optimization**, **Alerts**, and **About**. Health gauges, live telemetry
charts, the twin before/after comparison and energy analytics are all rendered client-side
with zero external dependencies.

---

## 🚀 Quick start

### Option A — Full stack (recommended)

Runs the FastAPI backend, which serves the dashboard and a live-updating simulated fleet.

```bash
# 1. Install dependencies (one time)
pip install -r backend/requirements.txt

# 2. Start the server
#    Windows:   run.bat
#    macOS/Linux / any:
python backend/main.py
```

Then open **http://localhost:8000** in your browser.
The sidebar will show **“Live · FastAPI backend”**.

### Option B — Dashboard only (no install)

The frontend ships with an in-browser fallback simulator, so it works even without the
backend:

```bash
# just open the file
frontend/index.html
```

The sidebar will show **“Demo mode · in-browser simulation.”** All six views are fully
functional — the data is generated in JavaScript instead of Python.

---

## 🏗️ Architecture

```
Industrial Machines → IoT Sensors → Edge Gateway → Cloud → AI Engine
                                      → Digital Twin → Recommendation Engine → Dashboard
```

```
machinesense-ai/
├── backend/
│   ├── main.py            # FastAPI app + REST API + serves the frontend
│   ├── simulator.py       # Industrial machine & IoT sensor simulator
│   ├── ml.py              # AI engine: health, anomalies, RUL, energy, twin, XAI
│   └── requirements.txt
├── frontend/
│   ├── index.html         # Dashboard shell
│   ├── styles.css         # Dark industrial theme
│   ├── charts.js          # Dependency-free canvas charts (line, gauge, donut)
│   ├── simulator.js       # In-browser fallback simulator (mirrors the backend)
│   └── app.js             # SPA: routing, API layer, all views
├── docs/
│   ├── MachineSenseAI_Pitch_Deck.pptx
│   ├── ONE_PAGER.md
│   └── build_deck.py
├── run.bat / run.sh
└── README.md
```

**Design note:** the frontend and backend implement the *same* AI logic (health scoring,
anomaly detection, RUL, digital twin) in Python and JavaScript. This keeps the demo reliable:
it looks and behaves identically whether the FastAPI backend is running or not.

---

## 🔌 API reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/overview` | Fleet KPIs + per-machine summaries |
| `GET`  | `/api/machines` | List of machines |
| `GET`  | `/api/machines/{id}` | Full detail: sensors, prediction, XAI, energy, recommendations |
| `GET`  | `/api/machines/{id}/history?n=60` | Time-series telemetry |
| `GET`  | `/api/alerts` | Active alerts (anomalies + threshold breaches) |
| `GET`  | `/api/meta` | Sensor config, fault types, twin actions |
| `POST` | `/api/machines/{id}/twin` | Run a digital-twin what-if — body: `{"action": "bearing_replacement"}` |
| `POST` | `/api/machines/{id}/inject-fault` | Demo: inject a fault — body: `{"fault": "overheating"}` |
| `POST` | `/api/machines/{id}/repair` | Demo: simulate a completed repair |
| `POST` | `/api/machines/{id}/power` | Start/stop a machine — body: `{"running": false}` |

Interactive API docs (Swagger UI) are auto-generated at **http://localhost:8000/docs**.

---

## 🧠 How the AI engine works

- **Health Score** — each sensor's deviation from its baseline toward its critical threshold
  is normalised to `[0,1]`, weighted by importance, and combined into a 0–100 score.
- **Anomaly detection** — a robust **median-absolute-deviation z-score** flags sudden
  deviations against each machine's own recent history (resistant to outliers).
- **RUL / failure risk** — least-squares slope of the recent health trend is extrapolated to
  a failure threshold; failure probability is a logistic function of health + degradation speed.
- **Energy** — average power draw vs. an ideal-load baseline yields efficiency, monthly cost,
  recoverable waste and CO₂ (India grid factor ≈ 0.82 kg/kWh, tariff ≈ ₹8.5/kWh).
- **Explainable AI** — the health penalty is attributed back to each sensor with a
  plain-language reason, so operators see *why*, not just a number.
- **Digital Twin** — models each maintenance action as a reduction of sensor severities and
  projects the resulting health, RUL, failure risk and energy savings — before any action.

---

## 🛠️ Technology stack

**Hardware (target):** ESP32 + vibration / current / sound / temperature sensors
**Software:** Python · FastAPI · React-ready frontend · PostgreSQL · Docker
**AI:** Time-series analysis · Anomaly detection · ML health scoring · Digital-twin models

> The prototype uses a pure-standard-library simulator so it runs anywhere Python does — the
> production system would ingest real sensor streams in place of the simulator.

---

## 📈 Project snapshot

- **Domain:** Industry 4.0 · AI · IoT · Digital Twin · Predictive Maintenance
- **Estimated project cost:** ₹19,80,000
- **Market:** 63M+ Indian MSMEs seeking affordable digital transformation
- **Model:** SaaS subscription + optional hardware kit & support

See [`docs/ONE_PAGER.md`](docs/ONE_PAGER.md) and the pitch deck in `docs/` for the full story.

---

*Built for the MSME Idea Hackathon.*
