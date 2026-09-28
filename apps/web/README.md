# apps/web — MachineSense AI dashboard

Single-page dashboard written in plain HTML, CSS and JavaScript. There is no framework,
no package manager and no build step; the files are served as-is.

| File | Role |
|---|---|
| `index.html` | Page shell; loads `charts.js`, `simulator.js`, `app.js` in that order |
| `styles.css` | Dark industrial theme |
| `charts.js` | Dependency-free canvas charts (line, gauge, donut) |
| `simulator.js` | In-browser fallback simulator that mirrors `apps/api` |
| `app.js` | Routing, API layer and all six views |

## How it gets data

On load, `app.js` calls `/api/overview` on the same origin. If that succeeds it uses the
FastAPI service ("Live · FastAPI backend"); otherwise, or if the service disappears
mid-session, it switches to `simulator.js` ("Demo mode · in-browser simulation"). The
active view refreshes every 2.5 s.

## Run

- **With the API (recommended):** start the server from the repo root (`run.bat` /
  `./run.sh`) and open http://localhost:8000 — `apps/api` serves these files.
- **Standalone:** open `index.html` directly in a browser; it runs in demo mode.
