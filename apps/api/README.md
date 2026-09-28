# apps/api — MachineSense AI service

FastAPI application that simulates a fleet of six industrial machines, runs the analytics
engine, exposes it as a REST API under `/api/*`, and serves the dashboard from `../web`.

| File | Role |
|---|---|
| `main.py` | FastAPI app, routes, background simulation tick (every 2 s), static hosting of `apps/web` |
| `simulator.py` | Machines, sensor streams (vibration, temperature, current, sound, power), fault injection |
| `ml.py` | Health score, MAD anomaly detection, RUL / failure risk, energy, XAI, digital twin, recommendations |
| `requirements.txt` | `fastapi`, `uvicorn[standard]`, `pydantic` |

`simulator.py` and `ml.py` use only the Python standard library. There is no database:
state is held in memory (last 240 readings per machine) and resets on restart. No
environment variables are read.

## Run

From the repository root:

```bash
pip install -r apps/api/requirements.txt
python -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
```

or simply `python apps/api/main.py` (port 8000, no reload). The dashboard directory is
resolved relative to `main.py`, so the working directory does not matter; if `apps/web` is
missing the server logs a warning and serves the API only.

Endpoints are listed in the [root README](../../README.md#api-reference) and live at
`http://localhost:8000/docs` while the server runs.
