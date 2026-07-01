"""FastAPI 应用入口——World 管理 + 消息队列 API / App entry: World CRUD + message queue API."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.config import load_config
from src.domain.message import Message
from src.domain.world import World
from src.mock import MOCK_WORLD, MockTickEngine
from src.repository.character_repo import CharacterRepo
from src.repository.event_repo import EventRepo
from src.repository.message_repo import MessageRepo
from src.repository.story_repo import StoryRepo
from src.repository.world_repo import WorldRepo
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

logger = logging.getLogger("aw.main")
setup_logging()

# 全局状态 / Global state
_cfg = load_config()
MOCK_MODE = _cfg.mock_mode

# session 管理 / Session store — world_id → {msg_repo, evt_repo, task, paused, done}
_sessions: dict[str, dict] = {}
# 共享 DB / Shared DB connection
_db: SQLiteClient | None = None


# 启动 seed test world / Seed test world on startup
async def _seed(rep: WorldRepo):
    rows = await rep.list_all()
    # 无 test world 则创建 / Create test world if missing
    if not any(r.id == "test" for r in rows):
        await rep.create(World(id="test", name="测试世界", pack_id="forgotten_realms"))
        logger.info("[Seed] test world created")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db  # noqa: PLW0603
    _db = SQLiteClient("data/world_db.db")
    await _db.connect()
    await _db.init_schema()
    await _seed(WorldRepo(_db))
    yield
    for mid in list(_sessions.keys()):
        s = _sessions.pop(mid, None)
        if s and (t := s.get("task")) and not t.done():
            t.cancel()
    if _db:
        await _db.close()


app = FastAPI(title="AIGameWorld API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --- World 管理 / World CRUD ---


@app.get("/api/world")
async def world_list():
    return [w.model_dump() for w in await WorldRepo(_db).list_all()]


@app.post("/api/world")
async def world_create(w: World):
    await WorldRepo(_db).create(w)
    return {"status": "ok"}


# --- Session 管理(按 world) / Session per world ---


@app.post("/api/world/{world_id}/session/start")
async def session_start(world_id: str):
    if world_id in _sessions:
        return {"status": "error", "detail": "session already exists"}
    msg_repo = MessageRepo(_db)
    evt_repo = EventRepo(_db)
    _sessions[world_id] = {
        "msg_repo": msg_repo,
        "evt_repo": evt_repo,
        "paused": False,
        "done": False,
    }
    task = asyncio.create_task(_graph_producer(world_id, msg_repo, evt_repo))
    _sessions[world_id]["task"] = task
    logger.info("[Main] %s started", world_id)
    return {"status": "ok"}


@app.get("/api/world/{world_id}/tick/next")
async def tick_next(world_id: str):
    s = _sessions.get(world_id)
    if not s:
        return {"type": "error", "data": {"message": "session not found"}}
    meta = await s["msg_repo"].get_next_pending(world_id)
    if meta:
        # 加载事件并组装 JSON / Load events + assemble JSON
        events = await s["evt_repo"].load_by_message(meta["id"], meta["tick"])
        return {
            "type": "tick",
            "data": {
                "id": meta["id"],
                "tick": meta["tick"],
                "timestamp": meta["created_at"],
                "events": [_event_to_dict(ev) for ev in events],
            },
        }
    if s.get("done"):
        return {"type": "done"}
    return {"type": "wait"}


@app.post("/api/world/{world_id}/tick/{tick}/ack")
async def tick_ack(world_id: str, tick: int):
    s = _sessions.get(world_id)
    if not s:
        return {"status": "error", "detail": "session not found"}
    await s["msg_repo"].ack(world_id, tick)
    return {"status": "ok"}


@app.post("/api/world/{world_id}/pause")
async def session_pause(world_id: str):
    s = _sessions.get(world_id)
    if not s:
        return {"status": "error", "detail": "session not found"}
    s["paused"] = True
    return {"status": "ok"}


@app.post("/api/world/{world_id}/resume")
async def session_resume(world_id: str):
    s = _sessions.get(world_id)
    if not s:
        return {"status": "error", "detail": "session not found"}
    s["paused"] = False
    return {"status": "ok"}


# --- 已有端点(不删) / Legacy endpoints ---


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/pack/{pack_id}/state")
async def get_pack_state(pack_id: str):
    if MOCK_MODE:
        return MOCK_WORLD
    try:
        scenes = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "description": r.get("description", ""),
                "exits": json.loads(r.get("exits_json", "[]")),
                "landmarks": json.loads(r.get("landmarks_json", "[]")),
                "environment": json.loads(r.get("environment_json", "{}")),
            }
            for r in await _db.fetch_all("SELECT * FROM scenes WHERE pack_id = ?", (pack_id,))
        ]
        pcs = [
            _char_from_row(r, True, i * 2 + 5)
            for i, r in enumerate(
                await _db.fetch_all("SELECT * FROM player_characters WHERE pack_id = ?", (pack_id,))
            )
        ]
        actors = [
            _char_from_row(r, False, i * 3 + 12)
            for i, r in enumerate(
                await _db.fetch_all("SELECT * FROM actors WHERE pack_id = ?", (pack_id,))
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
            for r in await _db.fetch_all("SELECT * FROM items WHERE pack_id = ?", (pack_id,))
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
            for r in await _db.fetch_all("SELECT * FROM scene_objects")
        ]
        return {
            "pack_id": pack_id,
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


@app.get("/view/global/events", response_class=HTMLResponse)
async def view_global_events(db: str = Query(default="data/world_db.db")):
    return await render_global_events(db_path=db)


@app.get("/view/global/narratives", response_class=HTMLResponse)
async def view_global_narratives(db: str = Query(default="data/world_db.db")):
    return await render_global_narratives(db_path=db)


@app.get("/view/global/meta", response_class=HTMLResponse)
async def view_global_meta(db: str = Query(default="data/world_db.db")):
    return await render_global_meta(db_path=db)


@app.get("/view/pack/{pack_id}", response_class=HTMLResponse)
async def view_pack(pack_id: str, db: str = Query(default="data/world_db.db")):
    return await render_pack(pack_id, db_path=db)


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
        "character_arc": json.loads(r.get("character_arc_json", "{}")) if is_pc else None,
        "functions": json.loads(r.get("functions_json", "[]")) if not is_pc else None,
        "is_pc": is_pc,
    }


# 后台 Graph 生产者 / Background Graph producer
async def _graph_producer(
    world_id: str,
    msg_repo: MessageRepo,
    evt_repo: EventRepo,
) -> None:
    """循环跑 tick → 写 messages + events / Loop: run tick → write 2 tables."""
    from src.domain.event import CharacterMoveEvent, DmNarrativeEvent, OpeningEvent

    try:
        if MOCK_MODE:
            engine = MockTickEngine()
            msg = Message(
                id=world_id,
                tick=0,
                world_id=world_id,
                timestamp=datetime.now(UTC),
                events=[OpeningEvent(text="冒险开始了！")],
            )
            await msg_repo.insert(msg)
            await evt_repo.insert_batch(msg.id, msg.tick, msg.events)
            while True:
                while _sessions.get(world_id, {}).get("paused"):
                    await asyncio.sleep(0.5)
                data = engine.generate_tick()
                events = [DmNarrativeEvent(text=data.get("narrative", ""))]
                events.extend(
                    CharacterMoveEvent(character_id=m["character_id"], x=m["x"], y=m["y"])
                    for m in data.get("character_moves", [])
                )
                msg = Message(
                    id=world_id,
                    tick=data["tick"],
                    world_id=world_id,
                    timestamp=datetime.now(UTC),
                    events=events,
                )
                await msg_repo.insert(msg)
                await evt_repo.insert_batch(msg.id, msg.tick, msg.events)
                logger.info("[Producer] %s tick=%d events=%d", world_id, msg.tick, len(msg.events))
        else:
            from src.graph.orchestrator import Orchestrator

            char_repo = CharacterRepo(_db)
            story_repo = StoryRepo(_db)
            orch = Orchestrator(session_id=world_id, repos={"char": char_repo, "story": story_repo})
            while True:
                while _sessions.get(world_id, {}).get("paused"):
                    await asyncio.sleep(0.5)
                result = await orch.run_tick()
                events = [DmNarrativeEvent(text=result.get("narrative", ""))]
                for a in result.get("character_actions", []):
                    events.append(
                        DmNarrativeEvent(
                            text=f"{a.get('character_id', '?')}: {a.get('description', '')}"
                        )
                    )
                msg = Message(
                    id=world_id,
                    tick=result["tick"],
                    world_id=world_id,
                    timestamp=datetime.now(UTC),
                    events=events,
                )
                await msg_repo.insert(msg)
                await evt_repo.insert_batch(msg.id, msg.tick, msg.events)
    except Exception as e:
        logger.error("[Producer] %s error: %s", world_id, e, exc_info=True)
    finally:
        if world_id in _sessions:
            _sessions[world_id]["done"] = True


# Event → JSON / Serialize event
def _event_to_dict(ev) -> dict:
    return ev.model_dump()
