"""FastAPI 依赖注入 / FastAPI dependencies.

所有路由共享的 DB 和 Orchestrator 获取逻辑集中在这里，
server.py 只负责应用生命周期和路由注册.
"""

from fastapi import Request

from src.orchestrator import Orchestrator
from src.storage.sqlite_client import SQLiteClient
from src.utils.metrics import MetricsCollector


def get_db(request: Request) -> SQLiteClient:
    """从 app.state 获取已初始化的 SQLiteClient."""
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise RuntimeError("DB not initialized")
    return db


def get_orch(request: Request) -> Orchestrator:
    """从 app.state 获取已初始化的 Orchestrator."""
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise RuntimeError("Orchestrator not initialized")
    return orch


def get_metrics_collector(request: Request) -> MetricsCollector:
    """从 app.state 获取 MetricsCollector."""
    mc = getattr(request.app.state, "metrics_collector", None)
    if mc is None:
        raise RuntimeError("MetricsCollector not initialized")
    return mc
