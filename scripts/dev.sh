#!/usr/bin/env bash
# Run the Invoice Review API and UI together from one terminal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=5173

# Background jobs get their own process groups so Ctrl+C can stop
# uvicorn --reload and Vite, not only the wrapper PIDs.
set -m

usage() {
  cat <<EOF
Usage: ./scripts/dev.sh [--check]

Start the FastAPI backend and Vite frontend together from the repo root.
Stop both with Ctrl+C.

  --check   Verify local tools, env files, and installs, then exit.
  --help    Show this help.
EOF
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing command: $1" >&2
    return 1
  fi
}

need_file() {
  if [[ ! -f "$1" ]]; then
    echo "missing file: $1" >&2
    return 1
  fi
}

need_dir() {
  if [[ ! -d "$1" ]]; then
    echo "missing directory: $1" >&2
    return 1
  fi
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}

check() {
  local failed=0

  echo "Checking Invoice Review..."
  need_cmd uv || failed=1
  need_cmd pnpm || failed=1
  need_file "$ROOT/backend/.env" || failed=1
  need_file "$ROOT/frontend/.env" || failed=1
  need_dir "$ROOT/backend/.venv" || {
    echo "  sync the backend first: cd backend && uv sync --locked" >&2
    failed=1
  }
  need_dir "$ROOT/frontend/node_modules" || {
    echo "  install the frontend first: cd frontend && pnpm install --frozen-lockfile" >&2
    failed=1
  }

  if ((failed)); then
    echo "Invoice Review is not ready to start." >&2
    exit 1
  fi

  echo "Invoice Review is ready to start."
}

start() {
  check

  if port_in_use "$BACKEND_PORT"; then
    echo "port $BACKEND_PORT is already in use" >&2
    exit 1
  fi
  if port_in_use "$FRONTEND_PORT"; then
    echo "port $FRONTEND_PORT is already in use" >&2
    exit 1
  fi

  echo
  echo "API  http://localhost:${BACKEND_PORT}"
  echo "UI   http://localhost:${FRONTEND_PORT}"
  echo "Stop with Ctrl+C"
  echo

  cleanup() {
    trap - EXIT INT TERM
    echo
    echo "Stopping Invoice Review..."
    if [[ -n "${backend_pid:-}" ]]; then
      kill -- -"$backend_pid" 2>/dev/null || true
    fi
    if [[ -n "${frontend_pid:-}" ]]; then
      kill -- -"$frontend_pid" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  (
    cd "$ROOT/backend"
    exec uv run --locked --no-sync uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port "$BACKEND_PORT"
  ) &
  backend_pid=$!

  (
    cd "$ROOT/frontend"
    exec pnpm dev
  ) &
  frontend_pid=$!

  wait "$backend_pid" "$frontend_pid"
}

case "${1:-}" in
  "" ) start ;;
  --check ) check ;;
  --help | -h ) usage ;;
  * )
    echo "unknown argument: $1" >&2
    usage >&2
    exit 1
    ;;
esac
