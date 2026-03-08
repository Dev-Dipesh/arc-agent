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
export ARC_MCP_HOST="${ARC_MCP_HOST:-${ARC_BRIDGE_HOST}}"
export ARC_MCP_PORT="${ARC_MCP_PORT:-${ARC_BRIDGE_PORT}}"
export ARC_MCP_TRANSPORT="${ARC_MCP_TRANSPORT:-sse}"
export FASTMCP_HOST="${ARC_MCP_HOST}"
export FASTMCP_PORT="${ARC_MCP_PORT}"

cd "${ROOT_DIR}"
PYTHONPATH="${ROOT_DIR}" uv --directory backend run python "${ROOT_DIR}/backend/mcp_server.py"
