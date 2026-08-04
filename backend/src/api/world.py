"""World CRUD 路由 / World CRUD routes."""

from fastapi import APIRouter, Depends

from src.api.deps import get_db
from src.domain.world import World
from src.repository.world_repo import WorldRepo
from src.utils.logging import log_api

router = APIRouter(prefix="/api/world", tags=["world"])


@router.get("")
async def world_list(db=Depends(get_db)):
    log_api("world.list", "-")
    return [w.model_dump() for w in await WorldRepo(db).list_all()]


@router.post("")
async def world_create(w: World, db=Depends(get_db)):
    await WorldRepo(db).create(w)
    return {"status": "ok"}
