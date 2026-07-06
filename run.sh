#!/usr/bin/env bash
# ============================================================
#  MachineSense AI - one-click launcher (macOS / Linux)
#  Installs dependencies (first run) and starts the server.
# ============================================================
set -e
cd "$(dirname "$0")"

echo
echo "  MachineSense AI - starting up..."
echo

python3 -m pip install -r backend/requirements.txt --quiet --disable-pip-version-check

echo
echo "  Dashboard will be available at:  http://localhost:8000"
echo "  Press Ctrl+C to stop."
echo

python3 -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
