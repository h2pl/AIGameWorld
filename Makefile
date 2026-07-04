# AIGameWorld 构建系统 / Build System
# 使用方式：make <target> 或 make help 查看所有命令 / Usage: make <target> or make help
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --no-print-directory

.PHONY: setup dev backend-dev frontend-dev test lint fmt docker-up clean help
.DEFAULT_GOAL := help

##@ 安装 / Setup

setup: ## 首次安装所有依赖 / Install all dependencies (first-time only)
	cd backend && uv sync
	cd frontend && npm install
	@echo "Done! Copy .env.example to .env and fill in DEEPSEEK_API_KEY"

##@ 开发 / Development

dev: ## 启动前后端（Ctrl+C 停止同时关闭）/ Start backend + frontend
	cd backend && uv run python -m uvicorn src.server:app --reload --port 8000 & \
	trap 'kill %1 2>/dev/null' EXIT; \
	cd "$(CURDIR)/frontend" && npm run dev

backend-dev: ## 仅启动后端 / Start backend only
	cd backend && uv run python -m uvicorn src.server:app --reload --port 8000

frontend-dev: ## 仅启动前端 / Start frontend only
	cd frontend && npm run dev

##@ 质量 / Quality

test: ## 运行全部测试 / Run all tests
	cd backend && uv run pytest
	cd frontend && npx vitest run --passWithNoTests

lint: ## Lint 全部代码 / Lint all code
	cd backend && uv run ruff check .
	cd frontend && npx eslint src/

fmt: ## 格式化全部代码 / Format all code
	cd backend && uv run ruff format .
	cd frontend && npx prettier --write src/

##@ 基础设施 / Infrastructure

docker-up: ## 用 Docker Compose 启动 / Start with Docker Compose
	docker compose -f docker/docker-compose.dev.yml up --build

clean: ## 清除构建产物和运行时数据 / Remove build artifacts and runtime data
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; true
	rm -rf data/*.db data/chroma/

help: ## 显示帮助 / Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	while read -r line; do \
		target=$$(echo "$$line" | cut -d: -f1); \
		desc=$$(echo "$$line" | sed 's/^.*## //'); \
		printf "  \033[36m%-15s\033[0m %s\n" "$$target" "$$desc"; \
	done
	@echo ""
	@echo "Usage: make <target>"
