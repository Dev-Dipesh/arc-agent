.PHONY: db-start db-stop bridge backend backend-up frontend stack stack-up lint

db-start:
	./scripts/start_db.sh

db-stop:
	./scripts/stop_db.sh

bridge:
	./scripts/start_bridge.sh

backend:
	./scripts/start_backend.sh

backend-up:
	./scripts/start_backend_up.sh

frontend:
	./scripts/start_frontend.sh

stack:
	./scripts/start_local_stack.sh

stack-up:
	./scripts/start_stack_up.sh

lint:
	cd backend && uv run ruff check .
