"""指标查询路由 / Metrics query routes."""

from fastapi import APIRouter, Query, Request

from src.utils.metrics import MetricsCollector

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _get_metrics_collector(request: Request) -> MetricsCollector | None:
    """从 app.state 获取 MetricsCollector / Get MetricsCollector from app.state."""
    return getattr(request.app.state, "metrics_collector", None)


@router.get("/ticks")
async def get_tick_metrics(
    request: Request,
    world_id: str = Query("", description="世界 ID / World ID"),
    last_n: int = Query(20, description="最近 N 条 / Last N records"),
):
    """获取最近 tick 指标 / Get recent tick metrics."""
    mc = _get_metrics_collector(request)
    if not mc:
        return {"ticks": [], "message": "metrics collector not initialized"}
    return {"ticks": mc.get_recent(world_id=world_id, last_n=last_n)}


@router.get("/summary")
async def get_metrics_summary(
    request: Request,
    world_id: str = Query("", description="世界 ID / World ID"),
    last_n: int = Query(100, description="聚合范围 / Aggregation range"),
):
    """获取聚合指标摘要 / Get aggregated metrics summary."""
    mc = _get_metrics_collector(request)
    if not mc:
        return {"message": "metrics collector not initialized"}
    return await mc.get_summary(world_id=world_id, last_n=last_n)


@router.get("/cost")
async def get_cost_metrics(
    request: Request,
    world_id: str = Query("", description="世界 ID / World ID"),
    last_n: int = Query(100, description="聚合范围 / Aggregation range"),
):
    """获取 Token 成本统计 / Get token cost statistics."""
    mc = _get_metrics_collector(request)
    if not mc:
        return {"message": "metrics collector not initialized"}
    summary = await mc.get_summary(world_id=world_id, last_n=last_n)
    return {
        "total_cost_usd": summary.get("total_cost_usd", 0),
        "total_tokens_in": summary.get("total_tokens_in", 0),
        "total_tokens_out": summary.get("total_tokens_out", 0),
        "avg_tokens_per_tick": summary.get("avg_tokens_per_tick", 0),
        "total_ticks": summary.get("total_ticks", 0),
    }
