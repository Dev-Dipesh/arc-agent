SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help bridge compose-up compose-down compose-logs backend-dev backend-up stack-dev stack-up lint

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
NC := \033[0m

help:
	@printf "%b\n" "$(BLUE)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@printf "%b\n" "$(BLUE)║                        Arc Agent Tasks                         ║$(NC)"
	@printf "%b\n" "$(BLUE)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@printf "\n"
	@printf "%b\n" "$(GREEN)Runtime$(NC)"
	@printf "%b\n" "  $(YELLOW)make stack-up$(NC)      - Start full stack: bridge + backend + frontend + Postgres"
	@printf "%b\n" "  $(YELLOW)make stack-dev$(NC)     - Start bridge + frontend + Postgres + langgraph dev (no langgraph-up license checks)"
	@printf "%b\n" "  $(YELLOW)make backend-up$(NC)    - Start langgraph up with compose addon + Postgres"
	@printf "%b\n" "  $(YELLOW)make backend-dev$(NC)   - Start langgraph dev (non-persistent checkpoints)"
	@printf "%b\n" "  $(YELLOW)make bridge$(NC)        - Start host Arc bridge only (foreground)"
	@printf "\n"
	@printf "%b\n" "$(GREEN)Docker Compose$(NC)"
	@printf "%b\n" "  $(YELLOW)make compose-up$(NC)    - Start frontend + Postgres"
	@printf "%b\n" "  $(YELLOW)make compose-down$(NC)  - Stop compose services"
	@printf "%b\n" "  $(YELLOW)make compose-logs$(NC)  - Follow compose logs"
	@printf "\n"
	@printf "%b\n" "$(GREEN)Quality$(NC)"
	@printf "%b\n" "  $(YELLOW)make lint$(NC)          - Run backend ruff checks"
	@printf "\n"
	@printf "%b\n" "$(CYAN)Shutdown$(NC)"
	@printf "%b\n" "  1) Press Ctrl+C in the terminal running make stack-up (stops bridge + backend)"
	@printf "%b\n" "  2) Run make compose-down (stops frontend + Postgres containers)"
	@printf "\n"
	@printf "%b\n" "$(RED)Note:$(NC) Arc automation requires the bridge to run on host macOS."

bridge:
	./scripts/start_bridge.sh

compose-up:
	COMPOSE_PROJECT_NAME=arc-agent docker compose -f docker/compose.yml up -d --build postgres frontend

compose-down:
	COMPOSE_PROJECT_NAME=arc-agent docker compose -f docker/compose.yml down

compose-logs:
	COMPOSE_PROJECT_NAME=arc-agent docker compose -f docker/compose.yml logs -f --tail=200 postgres frontend

backend-dev:
	cd backend && uv run langgraph dev --config langgraph.json --port "$${BACKEND_PORT:-2024}" --no-browser

backend-up:
	@set -a; [ -f .env ] && source .env; set +a; \
	POSTGRES_URI_EFFECTIVE="$${POSTGRES_URI_DOCKER:-}"; \
	if [[ -z "$$POSTGRES_URI_EFFECTIVE" && -n "$${POSTGRES_URI:-}" ]]; then \
		POSTGRES_URI_EFFECTIVE="$$(printf '%s' "$$POSTGRES_URI" | sed -E 's/@(localhost|127\.0\.0\.1):/@postgres:/')"; \
	fi; \
	if [[ -z "$$POSTGRES_URI_EFFECTIVE" ]]; then \
		echo "POSTGRES_URI_DOCKER (or POSTGRES_URI) must be set in .env"; \
		exit 1; \
	fi; \
	if [[ "$$POSTGRES_URI_EFFECTIVE" == *"@localhost:"* || "$$POSTGRES_URI_EFFECTIVE" == *"@127.0.0.1:"* ]]; then \
		echo "Postgres URI still points to localhost. Set POSTGRES_URI_DOCKER to use host 'postgres'."; \
		exit 1; \
	fi; \
	cd backend && ARC_BRIDGE_URL="$${ARC_BRIDGE_URL_DOCKER:-http://host.docker.internal:8765}" \
	COMPOSE_PROJECT_NAME=arc-agent \
	uv run langgraph up \
		--config langgraph.json \
		--docker-compose ../docker/compose.yml \
		--port "$${BACKEND_PORT:-2024}" \
		--postgres-uri "$$POSTGRES_URI_EFFECTIVE"

stack-up:
	@set -a; [ -f .env ] && source .env; set +a; \
	BRIDGE_PORT="$${ARC_BRIDGE_PORT:-8765}"; \
	BRIDGE_STARTED=0; \
	if lsof -nP -iTCP:"$$BRIDGE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Bridge port $$BRIDGE_PORT already in use; reusing existing bridge process."; \
	else \
		./scripts/start_bridge.sh & BRIDGE_PID=$$!; \
		BRIDGE_STARTED=1; \
		echo "Started bridge on port $$BRIDGE_PORT (pid $$BRIDGE_PID)."; \
	fi; \
	trap 'if [[ "$$BRIDGE_STARTED" = "1" ]]; then kill $$BRIDGE_PID 2>/dev/null || true; fi' EXIT INT TERM; \
	POSTGRES_URI_EFFECTIVE="$${POSTGRES_URI_DOCKER:-}"; \
	if [[ -z "$$POSTGRES_URI_EFFECTIVE" && -n "$${POSTGRES_URI:-}" ]]; then \
		POSTGRES_URI_EFFECTIVE="$$(printf '%s' "$$POSTGRES_URI" | sed -E 's/@(localhost|127\.0\.0\.1):/@postgres:/')"; \
	fi; \
	if [[ -z "$$POSTGRES_URI_EFFECTIVE" ]]; then \
		echo "POSTGRES_URI_DOCKER (or POSTGRES_URI) must be set in .env"; \
		exit 1; \
	fi; \
	if [[ "$$POSTGRES_URI_EFFECTIVE" == *"@localhost:"* || "$$POSTGRES_URI_EFFECTIVE" == *"@127.0.0.1:"* ]]; then \
		echo "Postgres URI still points to localhost. Set POSTGRES_URI_DOCKER to use host 'postgres'."; \
		exit 1; \
	fi; \
	cd backend && ARC_BRIDGE_URL="$${ARC_BRIDGE_URL_DOCKER:-http://host.docker.internal:8765}" \
	COMPOSE_PROJECT_NAME=arc-agent \
	uv run langgraph up \
		--config langgraph.json \
		--docker-compose ../docker/compose.yml \
		--port "$${BACKEND_PORT:-2024}" \
		--postgres-uri "$$POSTGRES_URI_EFFECTIVE"

stack-dev:
	@set -a; [ -f .env ] && source .env; set +a; \
	BRIDGE_PORT="$${ARC_BRIDGE_PORT:-8765}"; \
	BRIDGE_STARTED=0; \
	if lsof -nP -iTCP:"$$BRIDGE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Bridge port $$BRIDGE_PORT already in use; reusing existing bridge process."; \
	else \
		./scripts/start_bridge.sh & BRIDGE_PID=$$!; \
		BRIDGE_STARTED=1; \
		echo "Started bridge on port $$BRIDGE_PORT (pid $$BRIDGE_PID)."; \
	fi; \
	trap 'if [[ "$$BRIDGE_STARTED" = "1" ]]; then kill $$BRIDGE_PID 2>/dev/null || true; fi' EXIT INT TERM; \
	COMPOSE_PROJECT_NAME=arc-agent docker compose -f docker/compose.yml up -d --build postgres frontend; \
	cd backend && uv run langgraph dev --config langgraph.json --port "$${BACKEND_PORT:-2024}" --no-browser

lint:
	cd backend && uv run ruff check .
