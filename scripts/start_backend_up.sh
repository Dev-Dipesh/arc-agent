#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
ENV_FILE="${ROOT_DIR}/.env"
ADDONS_COMPOSE="${ROOT_DIR}/docker/compose.addons.yml"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

POSTGRES_URI_FOR_UP="${POSTGRES_URI_DOCKER:-${POSTGRES_URI:-}}"
if [[ -z "${POSTGRES_URI_FOR_UP}" ]]; then
  echo "POSTGRES_URI_DOCKER (or POSTGRES_URI) is required in .env for langgraph up."
  exit 1
fi

# Backend runs in container; host bridge must be reachable from container.
export ARC_BRIDGE_URL="${ARC_BRIDGE_URL_DOCKER:-http://host.docker.internal:8765}"

cd "${BACKEND_DIR}"
uv run langgraph up \
  --config langgraph.json \
  --docker-compose "${ADDONS_COMPOSE}" \
  --port "${BACKEND_PORT:-2024}" \
  --postgres-uri "${POSTGRES_URI_FOR_UP}"
