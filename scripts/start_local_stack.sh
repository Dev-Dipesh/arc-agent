#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"${ROOT_DIR}/scripts/start_db.sh"

echo "Starting backend and frontend..."
"${ROOT_DIR}/scripts/start_backend.sh" &
BACKEND_PID=$!

"${ROOT_DIR}/scripts/start_frontend.sh" &
FRONTEND_PID=$!

cleanup() {
  echo
  echo "Stopping local stack..."
  kill "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
}

trap cleanup INT TERM EXIT
wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
