"""FastAPI 应用入口 / FastAPI application entry point.

端点 / Endpoints:
  GET /health                   — 健康检查 / Health check
  GET /api/pack/{id}/state       — 返回 pack 世界状态 / World state for frontend
  GET /view                      — World Pack 查看器首页 / Viewer index (YAML + DB)
  GET /view/{pack_id}            — Pack 详情 / Pack detail
  WS /ws/{session_id}           — WebSocket 实时推送 / Real-time push
"""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.config import load_config
from src.mock import MOCK_WORLD
from src.storage.sqlite_client import SQLiteClient
from src.utils.logging import setup_logging
from src.viewer import (
    render_global_events,
    render_global_items,
    render_global_meta,
    render_global_narratives,
    render_global_objects,
    render_index,
    render_pack,
)
from src.ws import handle_ws

# 终端可见日志 / Terminal-visible logging
setup_logging()

# 配置：是否 mock 模式 / Config: mock mode toggle
_cfg = load_config()
MOCK_MODE = _cfg.mock_mode


@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期 / Lifecycle — 启动/关闭钩子."""
    yield


# FastAPI 应用 + CORS / App instance + CORS for frontend
app = FastAPI(
    title="AIGameWorld API",
    description="DM 驱动的 DND 世界模拟 / DM-driven DND world simulation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health_check():
    """健康检查 / Health check."""
    return {"status": "ok", "service": "AIGameWorld-backend"}


def _char_from_row(r: dict, is_pc: bool, pos_offset: int) -> dict:
    """DB row → 前端角色数据 / DB row → frontend character data."""
    cj = r.get("combat_json")
    return {
        "id": r["id"],
        "name": r["name"],
        "role": r["role"],
        "race": r.get("race"),
        "status": r.get("status", "active"),
        "scene_id": r["scene_id"],
        "position_x": r.get("position_x", pos_offset),  # 前端画布坐标 / canvas coords
        "position_y": r.get("position_y", 5 + pos_offset % 10),
        "attributes": json.loads(r["attributes_json"]),  # 六维属性 / 6 attributes
        "combat": json.loads(cj) if cj else None,  # 战斗数据可选 / combat optional
        "personality": r.get("personality", ""),
        "character_arc": json.loads(r.get("character_arc_json", "{}")) if is_pc else None,
        "functions": json.loads(r.get("functions_json", "[]")) if not is_pc else None,
        "is_pc": is_pc,
    }


@app.get("/api/pack/{pack_id}/state")
async def get_pack_state(pack_id: str):
    """返回 pack 的初始世界状态 / Return pack initial world state.

    前端加载时调用 → 返回场景/角色/物品/场景对象 / Called by frontend on load.
    """
    if MOCK_MODE:
        return MOCK_WORLD
    db = SQLiteClient("data/world_db.db")
    try:
        await db.connect()  # 连接 DB / connect
    except Exception as exc:
        raise HTTPException(status_code=503, detail="DB unavailable") from exc

    try:
        # 场景 / Scenes
        scenes = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "description": r.get("description", ""),
                "exits": json.loads(r.get("exits_json", "[]")),  # 出口列表
                "landmarks": json.loads(r.get("landmarks_json", "[]")),  # 地标列表
                "environment": json.loads(r.get("environment_json", "{}")),
            }
            for r in await db.fetch_all("SELECT * FROM scenes WHERE pack_id = ?", (pack_id,))
        ]

        # 主角团 / Player Characters
        pcs = [
            _char_from_row(r, True, i * 2 + 5)
            for i, r in enumerate(
                await db.fetch_all("SELECT * FROM player_characters WHERE pack_id = ?", (pack_id,))
            )
        ]

        # 配角 / Actors
        actors = [
            _char_from_row(r, False, i * 3 + 12)
            for i, r in enumerate(
                await db.fetch_all("SELECT * FROM actors WHERE pack_id = ?", (pack_id,))
            )
        ]

        # 物品 / Items
        items = [
            {
                "id": r["id"],
                "name": r["name"],
                "item_type": r["item_type"],
                "rarity": r.get("rarity", "common"),
                "description": r.get("description", ""),
            }
            for r in await db.fetch_all("SELECT * FROM items WHERE pack_id = ?", (pack_id,))
        ]

        # 场景对象 / Scene Objects
        scene_objects = [
            {
                "id": r["id"],
                "name": r["name"],
                "object_type": r["object_type"],
                "scene_id": r["scene_id"],
                "position_x": r.get("position_x", 0),
                "position_y": r.get("position_y", 0),
            }
            for r in await db.fetch_all("SELECT * FROM scene_objects")
        ]

        return {  # 组装返回 / assemble response
            "pack_id": pack_id,
            "scenes": scenes,
            "characters": pcs + actors,
            "items": items,
            "scene_objects": scene_objects,
        }
    finally:
        await db.close()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    """WebSocket 端点 / WebSocket endpoint — 前端驱动 tick 运行."""
    await handle_ws(ws, session_id)


@app.get("/view", response_class=HTMLResponse)
async def view_index(db: str = Query(default="data/world_db.db")):
    """DB 查看器首页 — pack 列表 + 全局入口."""
    return await render_index(db_path=db)


@app.get("/view/global/items", response_class=HTMLResponse)
async def view_global_items(db: str = Query(default="data/world_db.db")):
    """全部 Items（pack 无关）."""
    return await render_global_items(db_path=db)


@app.get("/view/global/scene-objects", response_class=HTMLResponse)
async def view_global_objects(db: str = Query(default="data/world_db.db")):
    """全部 Scene Objects（pack 无关）."""
    return await render_global_objects(db_path=db)


@app.get("/view/global/events", response_class=HTMLResponse)
async def view_global_events(db: str = Query(default="data/world_db.db")):
    """全部 Events（pack 无关）."""
    return await render_global_events(db_path=db)


@app.get("/view/global/narratives", response_class=HTMLResponse)
async def view_global_narratives(db: str = Query(default="data/world_db.db")):
    """叙事日志 — narratives 表."""
    return await render_global_narratives(db_path=db)


@app.get("/view/global/meta", response_class=HTMLResponse)
async def view_global_meta(db: str = Query(default="data/world_db.db")):
    """World Meta — world_meta 表."""
    return await render_global_meta(db_path=db)


@app.get("/view/pack/{pack_id}", response_class=HTMLResponse)
async def view_pack(pack_id: str, db: str = Query(default="data/world_db.db")):
    """Pack 详情页."""
    return await render_pack(pack_id, db_path=db)
