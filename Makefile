SHELL := /bin/bash
.DEFAULT_GOAL := help
BRIDGE_PID_FILE := .arc-agent-bridge.pid

.PHONY: help bridge bridge-stop compose-up compose-down compose-logs backend-dev backend-up stack-dev stack-up frontend-restart backend-restart lint

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
	@printf "%b\n" "  $(YELLOW)make stack-up$(NC)      - Start full stack: host MCP + backend + frontend + Postgres"
	@printf "%b\n" "  $(YELLOW)make stack-dev$(NC)     - Start host MCP + frontend + Postgres + langgraph dev (no langgraph-up license checks)"
	@printf "%b\n" "  $(YELLOW)make backend-up$(NC)    - Start langgraph up with compose addon + Postgres"
	@printf "%b\n" "  $(YELLOW)make backend-dev$(NC)   - Start langgraph dev (non-persistent checkpoints)"
	@printf "%b\n" "  $(YELLOW)make bridge$(NC)        - Start host Arc MCP server only (foreground)"
	@printf "%b\n" "  $(YELLOW)make bridge-stop$(NC)   - Stop managed host MCP server if running"
	@printf "\n"
	@printf "%b\n" "$(GREEN)Hot Reload (run alongside stack-up in a second terminal)$(NC)"
	@printf "%b\n" "  $(YELLOW)make frontend-restart$(NC) - Rebuild + restart only the frontend container"
	@printf "%b\n" "  $(YELLOW)make backend-restart$(NC)  - Rebuild + restart only the langgraph-api container"
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
	@printf "%b\n" "  Ctrl+C in make stack-up/stack-dev — stops langgraph + bridge only"
	@printf "%b\n" "  make compose-down                 — stops postgres + frontend (full teardown)"
	@printf "\n"
	@printf "%b\n" "$(RED)Note:$(NC) Arc automation requires the MCP server to run on host macOS."

bridge:
	./scripts/start_bridge.sh

bridge-stop:
	@set -euo pipefail; \
	BRIDGE_PORT="$${ARC_MCP_PORT:-$${ARC_BRIDGE_PORT:-8765}}"; \
	ROOT="$$(pwd)"; \
	if [[ -f "$(BRIDGE_PID_FILE)" ]]; then \
		PID="$$(cat "$(BRIDGE_PID_FILE)")"; \
		if kill -0 "$$PID" >/dev/null 2>&1; then \
			kill "$$PID" >/dev/null 2>&1 || true; \
			sleep 1; \
			if kill -0 "$$PID" >/dev/null 2>&1; then \
				kill -9 "$$PID" >/dev/null 2>&1 || true; \
			fi; \
			echo "Stopped managed bridge process $$PID."; \
		fi; \
		rm -f "$(BRIDGE_PID_FILE)"; \
	else \
		PID="$$(lsof -nP -iTCP:"$$BRIDGE_PORT" -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true)"; \
		if [[ -n "$$PID" ]]; then \
			kill "$$PID" >/dev/null 2>&1 || true; \
			sleep 1; \
			if kill -0 "$$PID" >/dev/null 2>&1; then \
				kill -9 "$$PID" >/dev/null 2>&1 || true; \
			fi; \
			echo "Stopped bridge listener on port $$BRIDGE_PORT (pid $$PID)."; \
		else \
			echo "No managed bridge PID file found and no listener on port $$BRIDGE_PORT."; \
		fi; \
	fi; \
	pkill -f "$$ROOT/scripts/start_bridge.sh" >/dev/null 2>&1 || true; \
	pkill -f "$$ROOT/backend/mcp_server.py" >/dev/null 2>&1 || true; \
	pkill -f "uv --directory backend run python $$ROOT/backend/mcp_server.py" >/dev/null 2>&1 || true

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
	cd backend && ARC_MCP_SSE_URL="$${ARC_MCP_SSE_URL_DOCKER:-http://host.docker.internal:8765/sse}" \
	COMPOSE_PROJECT_NAME=arc-agent \
	uv run langgraph up \
		--config langgraph.json \
		--docker-compose ../docker/compose.yml \
		--port "$${BACKEND_PORT:-2024}" \
		--postgres-uri "$$POSTGRES_URI_EFFECTIVE"

stack-up:
	@set -euo pipefail; \
	set -a; [ -f .env ] && source .env; set +a; \
	BRIDGE_PORT="$${ARC_MCP_PORT:-$${ARC_BRIDGE_PORT:-8765}}"; \
	BRIDGE_STARTED=0; \
	BRIDGE_PID=""; \
	MANAGED_PID=""; \
	if [[ -f "$(BRIDGE_PID_FILE)" ]]; then \
		MANAGED_PID="$$(cat "$(BRIDGE_PID_FILE)" 2>/dev/null || true)"; \
	fi; \
	if lsof -nP -iTCP:"$$BRIDGE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then \
		BRIDGE_PID="$$(lsof -nP -iTCP:"$$BRIDGE_PORT" -sTCP:LISTEN -t | head -n 1)"; \
		if [[ -n "$$MANAGED_PID" && "$$MANAGED_PID" == "$$BRIDGE_PID" ]]; then \
			BRIDGE_STARTED=1; \
			echo "Bridge port $$BRIDGE_PORT in use by managed process $$BRIDGE_PID; will clean up on exit."; \
		else \
			echo "Bridge port $$BRIDGE_PORT already in use by PID $$BRIDGE_PID; reusing without ownership."; \
		fi; \
	else \
		./scripts/start_bridge.sh & BRIDGE_PID=$$!; \
		BRIDGE_STARTED=1; \
		echo "$$BRIDGE_PID" > "$(BRIDGE_PID_FILE)"; \
		echo "Started bridge on port $$BRIDGE_PORT (pid $$BRIDGE_PID)."; \
	fi; \
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
	cleanup() { \
		echo; \
		if [[ "$$BRIDGE_STARTED" = "1" && -n "$$BRIDGE_PID" ]]; then \
			kill $$BRIDGE_PID 2>/dev/null || true; \
			rm -f "$(BRIDGE_PID_FILE)"; \
		fi; \
		echo "Stack stopped. Containers still running — use 'make compose-down' to remove them."; \
	}; \
	trap cleanup EXIT INT TERM; \
	cd backend && ARC_MCP_SSE_URL="$${ARC_MCP_SSE_URL_DOCKER:-http://host.docker.internal:8765/sse}" \
	COMPOSE_PROJECT_NAME=arc-agent \
	uv run langgraph up \
		--config langgraph.json \
		--docker-compose ../docker/compose.yml \
		--port "$${BACKEND_PORT:-2024}" \
		--postgres-uri "$$POSTGRES_URI_EFFECTIVE"

stack-dev:
	@set -euo pipefail; \
	set -a; [ -f .env ] && source .env; set +a; \
	BRIDGE_PORT="$${ARC_MCP_PORT:-$${ARC_BRIDGE_PORT:-8765}}"; \
	BRIDGE_STARTED=0; \
	BRIDGE_PID=""; \
	if lsof -nP -iTCP:"$$BRIDGE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Bridge port $$BRIDGE_PORT already in use; reusing existing bridge process."; \
	else \
		./scripts/start_bridge.sh & BRIDGE_PID=$$!; \
		BRIDGE_STARTED=1; \
		echo "Started bridge on port $$BRIDGE_PORT (pid $$BRIDGE_PID)."; \
	fi; \
	cleanup() { \
		echo; \
		if [[ "$$BRIDGE_STARTED" = "1" && -n "$$BRIDGE_PID" ]]; then \
			kill $$BRIDGE_PID 2>/dev/null || true; \
		fi; \
		echo "Dev backend stopped. Containers still running — use 'make compose-down' to remove them."; \
	}; \
	trap cleanup EXIT INT TERM; \
	COMPOSE_PROJECT_NAME=arc-agent docker compose -f docker/compose.yml up -d --build postgres frontend; \
	echo "Starting backend dev server on http://127.0.0.1:$${BACKEND_PORT:-2024} ..."; \
	cd backend && uv run langgraph dev --config langgraph.json --port "$${BACKEND_PORT:-2024}" --no-browser

frontend-restart:
	COMPOSE_PROJECT_NAME=arc-agent docker compose -f docker/compose.yml up -d --build frontend

backend-restart:
	COMPOSE_PROJECT_NAME=arc-agent docker compose -f docker/compose.yml up -d --build langgraph-api

lint:
	cd backend && uv run ruff check .
