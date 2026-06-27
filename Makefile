.PHONY: setup dev backend-dev frontend-dev test lint fmt docker-up clean help

setup:  ## First-time setup
	@echo "Backend:  cd backend && uv sync"
	@echo "Frontend: cd frontend && npm install"
	@echo "Copy .env.example to .env and fill in API keys"

dev:  ## Start both (run in separate terminals)
	@echo "Terminal 1: make backend-dev"
	@echo "Terminal 2: make frontend-dev"

backend-dev:  ## Start backend dev server
	cd backend && uv run uvicorn src.main:app --reload --port 8000

frontend-dev: ## Start frontend dev server
	cd frontend && npx vite --port 3000

test:   ## Run all tests
	cd backend && uv run pytest
	cd frontend && npx vitest run

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

help:   ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-15s %s\n", $$1, $$2}'
.DEFAULT_GOAL := help
