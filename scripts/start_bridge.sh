#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

export ARC_BRIDGE_HOST="${ARC_BRIDGE_HOST:-127.0.0.1}"
export ARC_BRIDGE_PORT="${ARC_BRIDGE_PORT:-8765}"

if [[ -z "${ARC_BRIDGE_API_KEY:-}" ]]; then
  echo "ARC_BRIDGE_API_KEY is required in .env"
  exit 1
fi

cd "${ROOT_DIR}"
PYTHONPATH="${ROOT_DIR}" uv --directory backend run python "${ROOT_DIR}/bridge/bridge_server.py"
