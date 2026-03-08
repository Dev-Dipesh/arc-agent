SHELL := /bin/bash

.PHONY: bridge compose-up compose-down compose-logs backend-dev backend-up stack-up lint

bridge:
	./scripts/start_bridge.sh

compose-up:
	docker compose -f docker/compose.yml up -d --build postgres frontend

compose-down:
	docker compose -f docker/compose.yml down

compose-logs:
	docker compose -f docker/compose.yml logs -f --tail=200 postgres frontend

backend-dev:
	cd backend && uv run langgraph dev --config langgraph.json --port "$${BACKEND_PORT:-2024}" --no-browser

backend-up:
	@set -a; [ -f .env ] && source .env; set +a; \
	if [[ -z "$${POSTGRES_URI_DOCKER:-$${POSTGRES_URI:-}}" ]]; then \
		echo "POSTGRES_URI_DOCKER (or POSTGRES_URI) must be set in .env"; \
		exit 1; \
	fi; \
	cd backend && ARC_BRIDGE_URL="$${ARC_BRIDGE_URL_DOCKER:-http://host.docker.internal:8765}" \
	uv run langgraph up \
		--config langgraph.json \
		--docker-compose ../docker/compose.yml \
		--port "$${BACKEND_PORT:-2024}" \
		--postgres-uri "$${POSTGRES_URI_DOCKER:-$${POSTGRES_URI:-}}"

stack-up:
	@set -a; [ -f .env ] && source .env; set +a; \
	./scripts/start_bridge.sh & BRIDGE_PID=$$!; \
	trap 'kill $$BRIDGE_PID 2>/dev/null || true' EXIT INT TERM; \
	if [[ -z "$${POSTGRES_URI_DOCKER:-$${POSTGRES_URI:-}}" ]]; then \
		echo "POSTGRES_URI_DOCKER (or POSTGRES_URI) must be set in .env"; \
		exit 1; \
	fi; \
	cd backend && ARC_BRIDGE_URL="$${ARC_BRIDGE_URL_DOCKER:-http://host.docker.internal:8765}" \
	uv run langgraph up \
		--config langgraph.json \
		--docker-compose ../docker/compose.yml \
		--port "$${BACKEND_PORT:-2024}" \
		--postgres-uri "$${POSTGRES_URI_DOCKER:-$${POSTGRES_URI:-}}"

lint:
	cd backend && uv run ruff check .
