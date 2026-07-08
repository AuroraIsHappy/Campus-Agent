#!/usr/bin/env bash
# Campus-Agent startup script (Linux/macOS/Git Bash)
# Starts the API + frontend dev server. For production, use Docker instead.
set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CAMPUS_HOME="${CAMPUS_HOME:-$PROJECT_ROOT/.campus-demo}"

# Find a Python with campus deps (prefer .venv, then system)
PYTHON=""
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif [ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "ERROR: No Python found. Install Python 3.10+ or set CAMPUS_PYTHON."
    exit 1
fi
echo "Using Python: $PYTHON ($($PYTHON --version 2>&1))"

# Make hermes_cli importable if the sibling clone exists
if [ -d "$PROJECT_ROOT/../hermes-agent" ]; then
    export PYTHONPATH="$PROJECT_ROOT/../hermes-agent:${PYTHONPATH:-}"
fi

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

echo "Starting Campus API on http://127.0.0.1:$API_PORT"
$PYTHON -m uvicorn campus.api.server:app --host 127.0.0.1 --port "$API_PORT" --app-dir "$PROJECT_ROOT" &
API_PID=$!

echo "Starting frontend on http://127.0.0.1:$WEB_PORT"
cd "$PROJECT_ROOT/frontend"
npm run dev -- --host 127.0.0.1 --port "$WEB_PORT" &
WEB_PID=$!

echo ""
echo "Campus-Agent is running:"
echo "  API:      http://127.0.0.1:$API_PORT/health"
echo "  Frontend: http://127.0.0.1:$WEB_PORT"
echo ""
echo "Press Ctrl+C to stop."
trap "kill $API_PID $WEB_PID 2>/dev/null; exit" INT TERM
wait
