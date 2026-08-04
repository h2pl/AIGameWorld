"""场景路由 / Scene routes — 返回场景 + 地图信息"""

from fastapi import APIRouter, Depends

from src.api.deps import get_db
from src.repository.scene_repo import SceneRepo

router = APIRouter(prefix="/api/world", tags=["scene"])


@router.get("/{world_id}/scenes")
async def list_scenes(world_id: str, db=Depends(get_db)):
    """返回 world 下所有场景的完整信息 / List all scenes with map metadata."""
    repo = SceneRepo(db)
    return await repo.list_scenes(world_id)


@router.get("/{world_id}/scenes/{scene_id}")
async def get_scene(world_id: str, scene_id: str, db=Depends(get_db)):
    """返回单个场景的完整信息 / Get a single scene with map metadata."""
    repo = SceneRepo(db)
    return await repo.get_scene(scene_id) or {}
