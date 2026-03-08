.PHONY: db-start db-stop bridge backend frontend stack lint

db-start:
	./scripts/start_db.sh

db-stop:
	./scripts/stop_db.sh

bridge:
	./scripts/start_bridge.sh

backend:
	./scripts/start_backend.sh

frontend:
	./scripts/start_frontend.sh

stack:
	./scripts/start_local_stack.sh

lint:
	cd backend && uv run ruff check .
