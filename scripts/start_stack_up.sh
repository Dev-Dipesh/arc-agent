#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting local Arc bridge (host process)..."
"${ROOT_DIR}/scripts/start_bridge.sh" &
BRIDGE_PID=$!

cleanup() {
  echo
  echo "Stopping local Arc bridge..."
  kill "${BRIDGE_PID}" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "Starting LangGraph + Postgres + frontend via langgraph up..."
"${ROOT_DIR}/scripts/start_backend_up.sh"
