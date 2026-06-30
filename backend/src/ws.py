"""WebSocket 实时推送 / WebSocket real-time push.

前端连 ws://localhost:8000/ws/{session_id}，发送命令驱动 tick。

协议 / Protocol:
  init → init_ok(返回角色列表)
  run N → tick × N → done
"""

import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.graph.orchestrator import Orchestrator
from src.repository.character_repo import CharacterRepo
from src.repository.story_repo import StoryRepo
from src.storage.sqlite_client import SQLiteClient

logger = logging.getLogger("aw.ws")  # 日志器 / Logger


async def handle_ws(ws: WebSocket, session_id: str) -> None:
    """WebSocket 主循环 / WebSocket main loop."""
    await ws.accept()
    logger.info("[WS] %s accepted", session_id)
    db: SQLiteClient | None = None
    orch: Orchestrator | None = None

    try:
        while True:
            raw = await ws.receive_text()  # 接收消息 / Receive message
            msg = json.loads(raw)  # 解析 JSON / Parse JSON
            cmd = msg.get("cmd", "")  # 命令 / Command
            logger.debug("[WS] %s recv: cmd=%s", session_id, cmd)

            if cmd == "init":
                pack_id = msg.get("pack_id", "")
                use_llm = msg.get("llm", False)
                if not pack_id:
                    logger.warning("[WS] %s init: missing pack_id", session_id)
                    await ws.send_json({"type": "error", "data": "missing pack_id"})
                    continue

                logger.info("[WS] %s init pack_id=%s llm=%s", session_id, pack_id, use_llm)
                db, orch = await _init_session(session_id, pack_id, use_llm)

                char_repo = CharacterRepo(db)
                pcs = await char_repo.load_pcs(pack_id)
                actors = await char_repo.load_actors(pack_id)
                chars = _serialize_characters(pcs, True) + _serialize_characters(
                    actors, False
                )  # 合并 PC+Actor
                logger.info(
                    "[WS] %s init_ok: %d PCs + %d Actors = %d chars",
                    session_id,
                    len(pcs),
                    len(actors),
                    len(chars),
                )

                await ws.send_json(
                    {
                        "type": "init_ok",
                        "data": {"pack_id": pack_id, "characters": chars, "tick": 0},
                    }
                )

            elif cmd == "run":
                if not orch or not db:
                    logger.warning("[WS] %s run: not initialized", session_id)
                    await ws.send_json({"type": "error", "data": "not initialized"})
                    continue
                n = msg.get("ticks", 1)
                logger.info("[WS] %s run: %d ticks starting", session_id, n)
                for _i in range(n):
                    result = await orch.run_tick()
                    t = result["tick"]
                    narrative = result.get("narrative", "")
                    actions = result.get("character_actions", [])
                    errors = result.get("errors", [])
                    logger.info(
                        "[WS] %s tick=%d narrative=%r actions=%d errors=%d",
                        session_id,
                        t,
                        narrative[:60] if narrative else "(empty)",
                        len(actions),
                        len(errors),
                    )
                    if errors:
                        logger.warning("[WS] %s tick=%d errors: %s", session_id, t, errors)

                    # Mock 角色移动：每 tick 随机走 1-2 格 / Random 1-2 tile move per tick
                    char_repo = CharacterRepo(db)  # 角色仓库 / Character repo
                    pcs = await char_repo.load_pcs()  # 主角团 / PCs
                    actors = await char_repo.load_actors()  # 配角 / Actors
                    char_moves: list[dict] = []  # 移动列表 / Move list
                    for ch in pcs + actors:  # 遍历所有角色 / Iterate all chars
                        px = getattr(ch.location, "position_x", 0) if hasattr(ch, "location") else 0
                        py = getattr(ch.location, "position_y", 0) if hasattr(ch, "location") else 0
                        dx = (hash(ch.id + str(t)) % 5) - 2  # 随机 -2..2 / Random offset
                        dy = (hash(ch.id + str(t) + "y") % 5) - 2
                        nx = max(0, min(39, px + dx))  # 限制在地图内 / Clamp to map
                        ny = max(0, min(29, py + dy))
                        char_moves.append({"character_id": ch.id, "x": nx, "y": ny})
                    logger.info("[WS] %s tick=%d moves=%d", session_id, t, len(char_moves))

                    await ws.send_json(
                        {
                            "type": "tick",
                            "data": {
                                "tick": t,
                                "narrative": narrative,
                                "character_actions": actions,
                                "character_moves": char_moves,
                                "events": result.get("events", []),
                                "errors": errors,
                            },
                        }
                    )
                logger.info("[WS] %s run: done, final tick=%d", session_id, orch.tick - 1)
                await ws.send_json({"type": "done", "data": {"tick": orch.tick - 1}})

            elif cmd == "ping":
                logger.debug("[WS] %s ping", session_id)
                await ws.send_json({"type": "pong"})

            else:
                logger.warning("[WS] %s unknown cmd: %s", session_id, cmd)
                await ws.send_json({"type": "error", "data": f"unknown command: {cmd}"})

    except WebSocketDisconnect:
        logger.info("[WS] %s disconnected", session_id)
    except Exception as exc:
        logger.error("[WS] %s unexpected error: %s", session_id, exc, exc_info=True)
    finally:
        if db:
            await db.close()
            logger.info("[WS] %s db closed", session_id)


async def _init_session(
    session_id: str, pack_id: str, use_llm: bool = False
) -> tuple[SQLiteClient, Orchestrator]:
    """初始化 DB + Orchestrator / Init DB + Orchestrator."""
    logger.info("[WS] %s init_session: opening DB", session_id)
    db = SQLiteClient("data/world_db.db")
    await db.connect()
    await db.init_schema()

    char_repo = CharacterRepo(db)
    story_repo = StoryRepo(db)
    repos = {"char": char_repo, "story": story_repo}

    llm = None
    if use_llm:
        logger.info("[WS] %s init_session: creating LLM client", session_id)
        from src.config import load_config
        from src.llm.llm_client import LLMClient

        config = load_config("../config.yaml")
        llm = LLMClient(config.llm)

    orch = Orchestrator(session_id=session_id, repos=repos, llm=llm)
    logger.info("[WS] %s init_session: orchestrator ready, llm=%s", session_id, bool(llm))
    return db, orch


def _serialize_characters(chars: list[Any], is_pc: bool) -> list[dict]:
    """序列化角色为前端格式 / Serialize characters to frontend format."""
    out = []
    for ch in chars:
        try:
            d = {
                "id": ch.id,
                "name": ch.name,
                "role": ch.role,
                "race": ch.race,
                "status": ch.status,
                "scene_id": ch.location.scene_id if hasattr(ch, "location") else "",
                "position_x": getattr(ch.location, "position_x", 0)
                if hasattr(ch, "location")
                else 0,
                "position_y": getattr(ch.location, "position_y", 0)
                if hasattr(ch, "location")
                else 0,
                "combat": {
                    "hp": ch.combat.hp,
                    "max_hp": ch.combat.max_hp,
                    "ac": ch.combat.ac,
                }
                if ch.combat
                else None,
                "personality": getattr(ch, "personality", ""),
                "is_pc": is_pc,
            }
            if is_pc:
                d["character_arc"] = {"stage": ch.character_arc.stage} if ch.character_arc else None
            else:
                d["functions"] = (
                    list(ch.functions) if hasattr(ch, "functions") and ch.functions else []
                )
            out.append(d)
        except Exception as exc:
            logger.error(
                "[WS] serialize char %s failed: %s", getattr(ch, "id", "?"), exc, exc_info=True
            )
    return out
