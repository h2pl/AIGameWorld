"""事件查询路由 / Event query routes."""

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_db
from src.repository.event_repo import TickEventRepo
from src.repository.world_repo import WorldRepo

router = APIRouter(prefix="/api/world", tags=["events"])


@router.get("/{world_id}/events")
async def get_events(
    world_id: str,
    since_tick: int = Query(0),
    tick_limit: int = Query(1),
    db=Depends(get_db),
):
    """获取 since_tick 之后的 tick 事件，支持按 tick 数量分页.

    事件面板用 tick_limit=1 保证一次只取一个展示 tick；
    历史面板用 tick_limit=N 实现分页加载。
    """
    repo = TickEventRepo(db)
    world_repo = WorldRepo(db)

    tick_limit = max(1, min(tick_limit, 20))
    start_tick = since_tick + 1
    end_tick = since_tick + tick_limit
    events = await repo.load_by_tick_range(world_id, start_tick, end_tick)
    data_tick = await world_repo.get_data_tick(world_id)
    display_tick = await world_repo.get_display_tick(world_id)

    if not events:
        return {"events": [], "display_tick": display_tick, "data_tick": data_tick}

    max_tick = max(e["tick"] for e in events)
    return {"events": events, "display_tick": max_tick, "data_tick": data_tick}
