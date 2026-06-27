SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

MAKEFLAGS += --no-print-directory

.PHONY: setup dev backend-dev frontend-dev test lint fmt docker-up clean help
.DEFAULT_GOAL := help

##@ Setup

setup: ## Install all dependencies (first-time only)
	cd backend && uv sync
	cd frontend && npm install
	@echo "Done! Copy .env.example to .env and fill in DEEPSEEK_API_KEY"

##@ Development

dev: ## Start backend + frontend (Ctrl+C to stop both)
	cd backend && uv run uvicorn src.main:app --reload --port 8000 & \
	trap 'kill %1 2>/dev/null' EXIT; \
	cd "$(CURDIR)/frontend" && npx vite --port 3000

backend-dev: ## Start backend only
	cd backend && uv run uvicorn src.main:app --reload --port 8000

frontend-dev: ## Start frontend only
	cd frontend && npx vite --port 3000

##@ Quality

test: ## Run all tests
	cd backend && uv run pytest
	cd frontend && npx vitest run --passWithNoTests

lint: ## Lint all code
	cd backend && uv run ruff check .
	cd frontend && npx eslint src/

fmt: ## Format all code
	cd backend && uv run ruff format .
	cd frontend && npx prettier --write src/

##@ Infrastructure

docker-up: ## Start with Docker Compose
	docker compose -f docker/docker-compose.dev.yml up --build

clean: ## Remove build artifacts and runtime data
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; true
	rm -rf data/*.db data/chroma/

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	while read -r line; do \
		target=$$(echo "$$line" | cut -d: -f1); \
		desc=$$(echo "$$line" | sed 's/^.*## //'); \
		printf "  \033[36m%-15s\033[0m %s\n" "$$target" "$$desc"; \
	done
	@echo ""
	@echo "Usage: make <target>"
