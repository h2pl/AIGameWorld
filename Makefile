.PHONY: setup dev backend-dev frontend-dev test lint fmt docker-up clean help

setup:  ## Install all dependencies (first-time only)
	cd backend && uv sync
	cd frontend && npm install
	@echo Done! Copy .env.example to .env and fill in DEEPSEEK_API_KEY

dev:  ## Start backend + frontend (Ctrl+C to stop both)
	cd backend && uv run uvicorn src.main:app --reload --port 8000 & \
	cd ../frontend && npx vite --port 3000

backend-dev:  ## Start backend only
	cd backend && uv run uvicorn src.main:app --reload --port 8000

frontend-dev: ## Start frontend only
	cd frontend && npx vite --port 3000

test:   ## Run all tests
	cd backend && uv run pytest
	cd frontend && npx vitest run --passWithNoTests

lint:   ## Lint all code
	cd backend && uv run ruff check .
	cd frontend && npx eslint src/

fmt:    ## Format all code
	cd backend && uv run ruff format .
	cd frontend && npx prettier --write src/

docker-up:  ## Start with Docker
	docker compose -f docker/docker-compose.dev.yml up --build

clean:  ## Remove artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name node_modules -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf data/*.db data/chroma/

help:   ## Show available commands
	@echo "  setup         Install all dependencies"
	@echo "  dev           Start backend + frontend"
	@echo "  backend-dev   Start backend only"
	@echo "  frontend-dev  Start frontend only"
	@echo "  test          Run all tests"
	@echo "  lint          Lint all code"
	@echo "  fmt           Format all code"
	@echo "  clean         Remove artifacts"
.DEFAULT_GOAL := help
