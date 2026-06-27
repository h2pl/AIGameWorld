# SimGameWorld 后端 Dockerfile / Backend Dockerfile
# 多阶段构建：builder（安装依赖）→ runtime（运行） / Multi-stage: builder → runtime
FROM python:3.14-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv  # uv 包管理器
COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project                       # 仅安装依赖 / Deps only
COPY . .
RUN uv sync --no-dev                                            # 安装项目本身 / Install project

FROM python:3.14-slim
WORKDIR /app
RUN useradd -r appuser            # 非 root 用户运行 / Non-root user
COPY --from=builder /app /app
USER appuser
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
