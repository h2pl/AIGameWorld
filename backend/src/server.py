"""FastAPI 应用入口 / App entry point.

World CRUD + Tick 执行 + DB Viewer.
Orchestrator 直接驱动 graph，无后台任务 / Orchestrator drives graph directly, no background tasks.
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.domain.world import World
from src.repository.event_repo import TickEventRepo
from src.repository.message_repo import TickMessageRepo
from src.repository.world_repo import WorldRepo
from src.storage.sqlite_client import SQLiteClient
from src.utils.logging import get_logger, log_api, setup_logging
from src.viewer import (
    render_global_events,
    render_global_items,
    render_global_meta,
    render_global_objects,
    render_global_records,
    render_index,
    render_pack,
)

logger = get_logger(__name__)


# ── Tick Loop Manager ──
class TickLoopManager:
    def __init__(self):
        self.running_worlds: dict[str, bool] = {}
        self.tasks: dict[str, asyncio.Task] = {}

    async def _loop(self, world_id: str, orch):
        logger.info(f"[loop] Started continuous tick loop for world {world_id}")
        while self.running_worlds.get(world_id, False):
            try:
                await orch.run_tick(world_id)
                await asyncio.sleep(0.5)  # Prevent CPU hogging
            except Exception as e:
                logger.error(f"[loop] Error in tick loop for {world_id}: {e}")
                self.running_worlds[world_id] = False
                break
        logger.info(f"[loop] Stopped continuous tick loop for world {world_id}")

    def start(self, world_id: str, orch):
        if self.running_worlds.get(world_id):
            return
        self.running_worlds[world_id] = True
        self.tasks[world_id] = asyncio.create_task(self._loop(world_id, orch))

    def stop(self, world_id: str):
        self.running_worlds[world_id] = False
        if world_id in self.tasks:
            # We don't cancel immediately to let the current tick finish gracefully
            pass


loop_manager = TickLoopManager()

try:
    from .config import load_config
    from .utils.logging import configure_console, configure_format

    _cfg = load_config("../config.yaml")
    configure_format(_cfg.logging.json_format)
    setup_logging()
    configure_console(_cfg.logging.console.model_dump())
except Exception:
    setup_logging()
    configure_console(None)

app = FastAPI(title="AIGameWorld API", version="0.1.0")


def _get_db() -> SQLiteClient:
    db = getattr(app.state, "db", None)
    if db is None:
        raise RuntimeError("DB not initialized")
    return db


def _get_orch():
    """获取全局 Orchestrator 单例."""
    if not hasattr(app.state, "orchestrator"):
        from src.graph.orchestrator import Orchestrator
        from src.llm.llm_client import LLMClient
        from src.repository.dm_record_repo import DMRecordRepo
        from src.repository.pc_repo import PcRepo
        from src.repository.scene_repo import SceneRepo
        from src.repository.world_repo import WorldRepo

        db = _get_db()
        cfg = load_config("../config.yaml")
        llm = LLMClient(cfg.llm, mock=cfg.mock.enabled, mock_dataset=cfg.mock.dataset)
        if cfg.mock.enabled:
            logger.info("[main] mock mode dataset=%s", cfg.mock.dataset)
        app.state.orchestrator = Orchestrator(
            llm=llm,
            repos={
                "char": PcRepo(db),
                "dm_record": DMRecordRepo(db),
                "scene": SceneRepo(db),
                "world": WorldRepo(db),
                "event": TickEventRepo(db),
                "message": TickMessageRepo(db),
            },
        )
    return app.state.orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SQLiteClient("data/world_db.db")
    app.state.db = db
    await db.connect()
    await db.init_schema()
    yield
    if app.state.db:
        await app.state.db.close()
        app.state.db = None


app.router.lifespan_context = lifespan
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── World CRUD ──


@app.get("/api/world")
async def world_list():
    log_api("world.list", "-")
    return [w.model_dump() for w in await WorldRepo(_get_db()).list_all()]


@app.post("/api/world")
async def world_create(w: World):
    await WorldRepo(_get_db()).create(w)
    return {"status": "ok"}


# ── Tick 执行（Orchestrator 直接驱动，无后台任务）──


@app.get("/api/world/{world_id}/tick/next")
async def tick_next(world_id: str):
    """运行一个 tick 并返回事件."""
    orch = _get_orch()
    result = await orch.run_tick(world_id)
    events = await _load_tick_events(result["tick_message_id"], result["tick"])
    return {
        "tick": result["tick"],
        "tick_message_id": result["tick_message_id"],
        "narrative": result.get("narrative", ""),
        "events": [_event_to_dict(ev) for ev in events],
    }


@app.post("/api/world/{world_id}/loop/start")
async def loop_start(world_id: str):
    """开始持续 Tick 循环."""
    loop_manager.start(world_id, _get_orch())
    return {"status": "ok", "running": True}


@app.post("/api/world/{world_id}/loop/pause")
async def loop_pause(world_id: str):
    """暂停持续 Tick 循环."""
    loop_manager.stop(world_id)
    return {"status": "ok", "running": False}


@app.post("/api/world/{world_id}/loop/resume")
async def loop_resume(world_id: str):
    """恢复持续 Tick 循环."""
    loop_manager.start(world_id, _get_orch())
    return {"status": "ok", "running": True}


@app.get("/api/world/{world_id}/loop/status")
async def loop_status(world_id: str):
    """获取循环状态."""
    return {"running": loop_manager.running_worlds.get(world_id, False)}


@app.get("/api/world/{world_id}/events")
async def get_events(world_id: str, since_tick: int = Query(0)):
    """获取指定 tick 之后的事件."""
    db = _get_db()
    repo = TickEventRepo(db)
    # We need to get the current tick to know the range
    world_repo = WorldRepo(db)
    world = await world_repo.get(world_id)
    current_tick = world.current_tick if world else 0

    if since_tick >= current_tick:
        return {"events": [], "current_tick": current_tick}

    events = await repo.load_by_tick_range(world_id, since_tick + 1, current_tick)
    return {"events": events, "current_tick": current_tick}


@app.post("/api/world/{world_id}/reset")
async def world_reset(world_id: str):
    """重置 world 的 tick 计数."""
    loop_manager.stop(world_id)
    await _get_orch().reset(world_id)
    return {"status": "ok"}


# ── World State + Health ──


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


async def _load_tick_events(tick_message_id: str, tick: int) -> list:
    """加载一个 tick 的事件列表."""
    if not tick_message_id:
        return []
    db = _get_db()
    evt_repo = TickEventRepo(db)
    return await evt_repo.load_by_message(tick_message_id, tick)


def _event_to_dict(ev) -> dict:
    if isinstance(ev, dict):
        return ev
    return ev.model_dump()
