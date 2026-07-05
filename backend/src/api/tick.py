"""Tick 执行路由 / Tick execution routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_db, get_orch
from src.repository.world_repo import WorldRepo
from src.tick_runner import batch_runner, loop_manager
from src.utils.logging import log_api

router = APIRouter(prefix="/api/world", tags=["tick"])


@router.get("/{world_id}/tick/next")
async def tick_next(world_id: str, orch=Depends(get_orch), db=Depends(get_db)):
    """运行一个 tick 并返回事件（data_tick 推进）."""
    result = await orch.run_tick(world_id)
    display_tick = await WorldRepo(db).get_display_tick(world_id)
    return {
        "tick": result["tick"],
        "display_tick": display_tick,
    }


@router.post("/{world_id}/loop/start")
async def loop_start(world_id: str, orch=Depends(get_orch)):
    """开始持续 Tick 循环."""
    loop_manager.start(world_id, orch)
    return {"status": "ok", "running": True}


@router.post("/{world_id}/loop/pause")
async def loop_pause(world_id: str):
    """暂停持续 Tick 循环."""
    loop_manager.stop(world_id)
    return {"status": "ok", "running": False}


@router.post("/{world_id}/loop/resume")
async def loop_resume(world_id: str, orch=Depends(get_orch)):
    """恢复持续 Tick 循环."""
    loop_manager.start(world_id, orch)
    return {"status": "ok", "running": True}


@router.get("/{world_id}/loop/status")
async def loop_status(world_id: str):
    """获取循环状态."""
    return {
        "running": loop_manager.running_worlds.get(world_id, False),
        "batch_running": batch_runner.is_running(world_id),
        "batch_target": batch_runner.get_target(world_id),
        "batch_completed": batch_runner.get_completed(world_id),
    }


@router.post("/{world_id}/tick/batch/{n}")
async def tick_batch(world_id: str, n: int, orch=Depends(get_orch)):
    """直接用 orchestrator 跑 N 个 tick（不返回数据，前端主动拉取）."""
    if n <= 0:
        raise HTTPException(status_code=400, detail="n must be positive")
    try:
        batch_runner.start(world_id, orch, n)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    log_api("tick.batch", f"{world_id}:{n}")
    return {"status": "ok", "n": n}


@router.post("/{world_id}/tick/display/{tick}")
async def set_display_tick(world_id: str, tick: int, db=Depends(get_db)):
    """前端展示完一个 tick 后，更新 display_tick."""
    if tick < 0:
        raise HTTPException(status_code=400, detail="tick must be non-negative")
    await WorldRepo(db).set_display_tick(world_id, tick)
    log_api("tick.display", f"{world_id}:{tick}")
    return {"status": "ok", "world_id": world_id, "display_tick": tick}
