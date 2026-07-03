"""FastAPI 应用入口 / App entry point.

World CRUD + 消息队列 API + DB Viewer.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.domain.world import World
from src.repository.event_repo import TickEventRepo
from src.repository.message_repo import TickMessageRepo
from src.repository.world_repo import WorldRepo
from src.storage.sqlite_client import SQLiteClient
from src.utils.logging import log_api, log_msg, setup_logging
from src.viewer import (
    render_global_events,
    render_global_items,
    render_global_meta,
    render_global_objects,
    render_global_records,
    render_index,
    render_pack,
)

logger = logging.getLogger("aw.main")
setup_logging()

app = FastAPI(title="AIGameWorld API", version="0.1.0")


# 运行时 session 注册表 / Runtime session registry
def _get_sessions() -> dict[str, dict]:
    sessions = getattr(app.state, "sessions", None)
    if sessions is None:
        sessions = {}
        app.state.sessions = sessions
    return sessions


# 统一读取共享 DB 连接 / Unified accessor for shared DB connection
def _get_db() -> SQLiteClient:
    db = getattr(app.state, "db", None)
    if db is None:
        raise RuntimeError("DB not initialized")
    return db


# 统一写入共享 DB 连接 / Unified setter for shared DB connection
def _set_db(db: SQLiteClient | None) -> None:
    app.state.db = db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化共享资源 / Initialize shared resources on startup
    db = SQLiteClient("data/world_db.db")
    _set_db(db)
    app.state.sessions = {}
    await db.connect()
    await db.init_schema()
    yield
    # 关闭时回收 session 与 DB / Clean up sessions and DB on shutdown
    sessions = _get_sessions()
    for mid in list(sessions.keys()):
        s = sessions.pop(mid, None)
        if s and (t := s.get("task")) and not t.done():
            t.cancel()
    if getattr(app.state, "db", None):
        await db.close()
        _set_db(None)


app.router.lifespan_context = lifespan
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --- World 管理 / World CRUD ---


@app.get("/api/world")
async def world_list():
    return [w.model_dump() for w in await WorldRepo(_get_db()).list_all()]


@app.post("/api/world")
async def world_create(w: World):
    await WorldRepo(_get_db()).create(w)
    return {"status": "ok"}


# --- Session 管理(按 world) / Session per world ---


@app.post("/api/world/{world_id}/session/start")
async def session_start(world_id: str):
    sessions = _get_sessions()
    if world_id in sessions:
        return {"status": "error", "detail": "session already exists"}
    db = _get_db()
    msg_repo = TickMessageRepo(db)
    evt_repo = TickEventRepo(db)
    sessions[world_id] = {
        "msg_repo": msg_repo,
        "evt_repo": evt_repo,
        "paused": False,
        "done": False,
    }
    task = asyncio.create_task(_graph_producer(world_id, msg_repo, evt_repo))
    sessions[world_id]["task"] = task
    log_api("start", world_id)
    return {"status": "ok"}


@app.get("/api/world/{world_id}/tick/next")
async def tick_next(world_id: str):
    s = _get_sessions().get(world_id)
    if not s:
        return {"type": "error", "data": {"message": "session not found"}}
    meta = await s["msg_repo"].get_next_pending(world_id)
    if meta:
        tick_events = await s["evt_repo"].load_by_message(meta["id"], meta["tick"])
        log_msg("pull", world_id, meta["tick"], event_count=len(tick_events))
        return {
            "type": "tick",
            "data": {
                "id": meta["id"],
                "tick": meta["tick"],
                "timestamp": meta["created_at"],
                "events": [_event_to_dict(ev) for ev in tick_events],
            },
        }
    if s.get("done"):
        log_api("done", world_id)
        return {"type": "done"}
    return {"type": "wait"}


@app.post("/api/world/{world_id}/tick/{tick}/ack")
async def tick_ack(world_id: str, tick: int):
    s = _get_sessions().get(world_id)
    if not s:
        return {"status": "error", "detail": "session not found"}
    await s["msg_repo"].ack(world_id, tick)
    log_msg("ack", world_id, tick)
    return {"status": "ok"}


@app.post("/api/world/{world_id}/pause")
async def session_pause(world_id: str):
    s = _get_sessions().get(world_id)
    if not s:
        return {"status": "error", "detail": "session not found"}
    s["paused"] = True
    log_api("pause", world_id)
    return {"status": "ok"}


@app.post("/api/world/{world_id}/resume")
async def session_resume(world_id: str):
    s = _get_sessions().get(world_id)
    if not s:
        return {"status": "error", "detail": "session not found"}
    s["paused"] = False
    log_api("resume", world_id)
    return {"status": "ok"}


# --- 已有端点(不删) / Legacy endpoints ---


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AIGameWorld-backend"}


@app.get("/api/world/{world_id}/state")
async def get_pack_state(world_id: str):
    try:
        db = _get_db()
        scenes = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "description": r.get("description", ""),
            }
            for r in await db.fetch_all("SELECT * FROM scenes WHERE world_id = ?", (world_id,))
        ]
        pcs = [
            _char_from_row(r, True, i * 2 + 5)
            for i, r in enumerate(
                await db.fetch_all(
                    "SELECT * FROM player_characters WHERE world_id = ?", (world_id,)
                )
            )
        ]
        actors = [
            _char_from_row(r, False, i * 3 + 12)
            for i, r in enumerate(
                await db.fetch_all("SELECT * FROM actors WHERE world_id = ?", (world_id,))
            )
        ]
        items = [
            {
                "id": r["id"],
                "name": r["name"],
                "item_type": r["item_type"],
                "rarity": r.get("rarity", "common"),
                "description": r.get("description", ""),
            }
            for r in await db.fetch_all("SELECT * FROM items WHERE world_id = ?", (world_id,))
        ]
        so = [
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
        return {
            "world_id": world_id,
            "scenes": scenes,
            "characters": pcs + actors,
            "items": items,
            "scene_objects": so,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="DB unavailable") from exc


# --- View ---


@app.get("/view", response_class=HTMLResponse)
async def view_index(db: str = Query(default="data/world_db.db")):
    return await render_index(db_path=db)


@app.get("/view/global/items", response_class=HTMLResponse)
async def view_global_items(db: str = Query(default="data/world_db.db")):
    return await render_global_items(db_path=db)


@app.get("/view/global/scene-objects", response_class=HTMLResponse)
async def view_global_objects(db: str = Query(default="data/world_db.db")):
    return await render_global_objects(db_path=db)


@app.get("/view/global/tick_events", response_class=HTMLResponse)
async def view_global_tick_events(db: str = Query(default="data/world_db.db")):
    return await render_global_events(db_path=db)


@app.get("/view/global/dm_records", response_class=HTMLResponse)
async def view_global_records(db: str = Query(default="data/world_db.db")):
    return await render_global_records(db_path=db)


@app.get("/view/global/meta", response_class=HTMLResponse)
async def view_global_meta(db: str = Query(default="data/world_db.db")):
    return await render_global_meta(db_path=db)


@app.get("/view/pack/{world_id}", response_class=HTMLResponse)
async def view_pack(world_id: str, db: str = Query(default="data/world_db.db")):
    return await render_pack(world_id, db_path=db)


# --- Internal ---


def _char_from_row(r: dict, is_pc: bool, pos_offset: int) -> dict:
    cj = r.get("combat_json")
    return {
        "id": r["id"],
        "name": r["name"],
        "role": r["role"],
        "race": r.get("race"),
        "status": r.get("status", "active"),
        "scene_id": r["scene_id"],
        "position_x": r.get("position_x", pos_offset),
        "position_y": r.get("position_y", 5 + pos_offset % 10),
        "attributes": json.loads(r["attributes_json"]),
        "combat": json.loads(cj) if cj else None,
        "personality": r.get("personality", ""),
        "arc": json.loads(r.get("arc_json", "{}")) if is_pc else None,
        "functions": json.loads(r.get("functions_json", "[]")) if not is_pc else None,
        "is_pc": is_pc,
    }


async def _graph_producer(
    world_id: str,
    msg_repo: TickMessageRepo,
    evt_repo: TickEventRepo,
) -> None:
    """Graph 生产者——Orchestrator 循环 / Graph producer: Orchestrator loop."""
    from src.config import load_config
    from src.graph.orchestrator import Orchestrator
    from src.llm.llm_client import LLMClient
    from src.repository.dm_record_repo import DMRecordRepo

    from .pc_repo import PcRepo

    db = _get_db()
    pc_repo = PcRepo(db)
    record_repo = DMRecordRepo(db)

    # 根据 config.yaml mock 配置创建对应的 LLMClient / Create LLMClient based on config.yaml mock settings
    llm = None
    config = load_config("../config.yaml")
    if config.mock.enabled:
        llm = LLMClient(config.llm, mock=True, mock_dataset=config.mock.dataset)
        logger.info("[Producer] mock mode dataset=%s", config.mock.dataset)

    orch = Orchestrator(
        session_id=world_id,
        llm=llm,
        repos={"char": pc_repo, "dm_record": record_repo},
    )
    try:
        while True:
            while _get_sessions().get(world_id, {}).get("paused"):
                await asyncio.sleep(0.5)
            await orch.run_tick()
    except Exception as e:
        logger.error("[Producer] %s error: %s", world_id, e, exc_info=True)
    finally:
        sessions = _get_sessions()
        if world_id in sessions:
            sessions[world_id]["done"] = True


# Event → JSON / Serialize event
def _event_to_dict(ev) -> dict:
    if isinstance(ev, dict):
        return ev
    return ev.model_dump()
