#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
RESEARCH_DESK_PORT="${RESEARCH_DESK_PORT:-8000}"
if [[ ! -x .venv/bin/python ]]; then
  RESEARCH_DESK_PYTHON="${RESEARCH_DESK_PYTHON:-}"
  if [[ -z "$RESEARCH_DESK_PYTHON" ]]; then
    for candidate in python3.12 python3.11 python3.10 python3 /usr/bin/python3; do
      if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(not ((3,9) <= sys.version_info[:2] <= (3,12)))' 2>/dev/null; then
        RESEARCH_DESK_PYTHON="$candidate"
        break
      fi
    done
  fi
  if [[ -z "$RESEARCH_DESK_PYTHON" ]] || ! "$RESEARCH_DESK_PYTHON" -c 'import sys; raise SystemExit(not ((3,9) <= sys.version_info[:2] <= (3,12)))'; then
    echo 'Install Python 3.11 or set RESEARCH_DESK_PYTHON to a Python 3.9–3.12 interpreter.'
    exit 1
  fi
  "$RESEARCH_DESK_PYTHON" -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python - "$RESEARCH_DESK_PORT" <<'PY'
import socket, sys, urllib.request
try:
    port = int(sys.argv[1])
    assert 1 <= port <= 65535
except (ValueError, AssertionError):
    raise SystemExit('RESEARCH_DESK_PORT must be a number between 1 and 65535.')
with socket.socket() as sock:
    try:
        sock.bind(('127.0.0.1', port))
    except OSError:
        print(f'Port {port} is already in use. Open http://127.0.0.1:{port} if Research Desk is running.')
        print('To load updates, press Ctrl+C in its terminal first, then run this script again.')
        print('Or start another instance with RESEARCH_DESK_PORT=8002 ./scripts/start.sh')
        raise SystemExit(1)
PY
if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm ci)
fi
(cd frontend && npm run build)
APP_PID=''
OLLAMA_PID=''
cleanup() {
  if [[ -n "$APP_PID" ]]; then kill -TERM "$APP_PID" 2>/dev/null || true; wait "$APP_PID" 2>/dev/null || true; fi
  if [[ -n "$OLLAMA_PID" ]]; then kill -TERM "$OLLAMA_PID" 2>/dev/null || true; wait "$OLLAMA_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if command -v ollama >/dev/null 2>&1; then
  if ! .venv/bin/python - <<'PY'
import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=2).close()
except OSError:
    raise SystemExit(1)
PY
  then
    mkdir -p .logs
    ./scripts/start-ollama.sh > .logs/ollama.log 2>&1 &
    OLLAMA_PID=$!
    .venv/bin/python - <<'PY'
import time, urllib.request
for _ in range(40):
    try:
        urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=1).close()
        print('Local model server ready.')
        break
    except OSError:
        time.sleep(.25)
else:
    print('Local model server did not start. Source excerpts still work; see .logs/ollama.log.')
PY
  fi
fi
printf 'Open http://127.0.0.1:%s — Ctrl+C stops this session.\n' "$RESEARCH_DESK_PORT"
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$RESEARCH_DESK_PORT" &
APP_PID=$!
wait "$APP_PID"
