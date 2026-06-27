"""FastAPI 应用入口 / FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 / Application lifecycle.
    Startup: 加载配置、初始化世界状态（将来）/ Load config, init world state (future).
    Shutdown: 持久化世界状态（将来）/ Persist world state (future).
    """
    yield


app = FastAPI(
    title="AIGameWorld API",
    description="DM 驱动的 DND 世界模拟 / DM-driven DND world simulation",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """健康检查端点 / Health check endpoint."""
    return {"status": "ok", "service": "AIGameWorld-backend"}
