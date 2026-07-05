"""World 重置路由 / World reset routes."""

from fastapi import APIRouter, Depends

from src.api.deps import get_db, get_orch
from src.repository.event_repo import TickEventRepo
from src.tick_runner import loop_manager
from src.utils.logging import log_api

router = APIRouter(prefix="/api/world", tags=["reset"])


@router.post("/{world_id}/reset")
async def world_reset(world_id: str, orch=Depends(get_orch), db=Depends(get_db)):
    """重置 world：清零 tick + 删除事件/DM记录."""
    loop_manager.stop(world_id)
    await orch.reset(world_id)
    await TickEventRepo(db).delete_by_world(world_id)
    await db.execute("DELETE FROM dm_records WHERE world_id = ?", (world_id,))
    await db.execute("DELETE FROM story_summaries WHERE world_id = ?", (world_id,))
    await db.commit()
    log_api("world.reset", world_id)
    return {"status": "ok"}
