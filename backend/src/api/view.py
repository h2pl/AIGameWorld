"""DB 查看器路由 / DB viewer routes."""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.viewer import (
    render_global_events,
    render_global_items,
    render_global_meta,
    render_global_objects,
    render_global_records,
    render_index,
    render_pack,
)

# 查看器路由前缀 / Viewer router (no prefix, paths start with /view)
router = APIRouter(tags=["view"])


# 首页 / Index page
@router.get("/view", response_class=HTMLResponse)
async def view_index(db: str = Query(default="data/world_db.db")):
    return await render_index(db_path=db)


# 全局物品 / Global items list
@router.get("/view/global/items", response_class=HTMLResponse)
async def view_global_items(db: str = Query(default="data/world_db.db")):
    return await render_global_items(db_path=db)


# 全局场景物体 / Global scene objects list
@router.get("/view/global/scene-objects", response_class=HTMLResponse)
async def view_global_objects(db: str = Query(default="data/world_db.db")):
    return await render_global_objects(db_path=db)


# 全局 tick 事件 / Global tick events list
@router.get("/view/global/tick_events", response_class=HTMLResponse)
async def view_global_tick_events(db: str = Query(default="data/world_db.db")):
    return await render_global_events(db_path=db)


# 全局 DM 记录 / Global DM records list
@router.get("/view/global/dm_records", response_class=HTMLResponse)
async def view_global_records(db: str = Query(default="data/world_db.db")):
    return await render_global_records(db_path=db)


# 全局元信息 / Global meta info
@router.get("/view/global/meta", response_class=HTMLResponse)
async def view_global_meta(db: str = Query(default="data/world_db.db")):
    return await render_global_meta(db_path=db)


# 单个 world 详情 / Single world detail page
@router.get("/view/pack/{world_id}", response_class=HTMLResponse)
async def view_pack(world_id: str, db: str = Query(default="data/world_db.db")):
    return await render_pack(world_id, db_path=db)
