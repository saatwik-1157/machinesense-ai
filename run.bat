@echo off
REM ============================================================
REM  MachineSense AI - one-click launcher (Windows)
REM  Installs dependencies (first run) and starts the server.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo   MachineSense AI - starting up...
echo.

REM Install API dependencies (safe to run every time)
python -m pip install -r apps\api\requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
  echo   [!] Dependency install failed. Ensure Python 3.10+ is installed and on PATH.
  pause
  exit /b 1
)

echo.
echo   Dashboard will be available at:  http://localhost:8000
echo   Press Ctrl+C to stop.
echo.

REM Start the FastAPI server (serves the dashboard too)
python -m uvicorn main:app --app-dir apps\api --host 127.0.0.1 --port 8000

endlocal
