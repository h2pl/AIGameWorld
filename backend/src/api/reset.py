"""World 重置路由 / World reset routes."""

from fastapi import APIRouter, Depends

from src.api.deps import get_orch
from src.tick_runner import loop_manager
from src.utils.logging import log_api

router = APIRouter(prefix="/api/world", tags=["reset"])


@router.post("/{world_id}/reset")
async def world_reset(world_id: str, orch=Depends(get_orch)):
    """重置 world：清零 tick + 清理事件/DM记录 + 重置角色坐标."""
    loop_manager.stop(world_id)
    await orch.reset(world_id)
    log_api("world.reset", world_id)
    return {"status": "ok"}
