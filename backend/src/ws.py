"""WebSocket 实时推送 / WebSocket real-time push.

前端连 ws://localhost:8000/ws/{session_id}，发送命令驱动 tick。
"""

import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.graph.orchestrator import Orchestrator
from src.repository.character_repo import CharacterRepo
from src.repository.story_repo import StoryRepo
from src.storage.sqlite_client import SQLiteClient


async def handle_ws(ws: WebSocket, session_id: str) -> None:
    """WebSocket 主循环 / WebSocket main loop."""
    await ws.accept()
    db: SQLiteClient | None = None
    orch: Orchestrator | None = None

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            cmd = msg.get("cmd", "")

            if cmd == "init":
                # 初始化：加载 pack 数据 / Init: load pack data
                pack_id = msg.get("pack_id", "")
                if not pack_id:
                    await ws.send_json({"type": "error", "data": "missing pack_id"})
                    continue
                db, orch = await _init_session(session_id, pack_id)
                # 返回初始世界状态 / Return initial world state
                char_repo = CharacterRepo(db)
                pcs = await char_repo.load_pcs(pack_id)
                actors = await char_repo.load_actors(pack_id)
                await ws.send_json(
                    {
                        "type": "init_ok",
                        "data": {
                            "pack_id": pack_id,
                            "characters": _serialize_characters(pcs, True)
                            + _serialize_characters(actors, False),
                            "tick": 0,
                        },
                    }
                )

            elif cmd == "run":
                # 运行 N 个 tick / Run N ticks
                if not orch or not db:
                    await ws.send_json({"type": "error", "data": "not initialized"})
                    continue
                n = msg.get("ticks", 1)
                for _ in range(n):
                    result = await orch.run_tick()
                    await ws.send_json(
                        {
                            "type": "tick",
                            "data": {
                                "tick": result["tick"],
                                "narrative": result.get("narrative", ""),
                                "character_actions": result.get("character_actions", []),
                                "events": result.get("events", []),
                                "errors": result.get("errors", []),
                            },
                        }
                    )
                await ws.send_json({"type": "done", "data": {"tick": orch.tick - 1}})

            elif cmd == "ping":
                await ws.send_json({"type": "pong"})

            else:
                await ws.send_json({"type": "error", "data": f"unknown command: {cmd}"})

    except WebSocketDisconnect:
        pass
    finally:
        if db:
            await db.close()


async def _init_session(session_id: str, pack_id: str) -> tuple[SQLiteClient, Orchestrator]:
    """初始化 DB + Orchestrator / Init DB + Orchestrator."""
    db = SQLiteClient("data/world_db.db")
    await db.connect()
    await db.init_schema()  # noqa: S608

    char_repo = CharacterRepo(db)
    story_repo = StoryRepo(db)
    repos = {"char": char_repo, "story": story_repo}

    orch = Orchestrator(session_id=session_id, repos=repos)
    return db, orch


def _serialize_characters(chars: list[Any], is_pc: bool) -> list[dict]:
    """序列化角色 / Serialize characters."""
    out = []
    for ch in chars:
        d = {
            "id": ch.id,
            "name": ch.name,
            "role": ch.role,
            "race": ch.race,
            "status": ch.status,
            "scene_id": ch.location.scene_id if hasattr(ch, "location") else "",
            "position_x": getattr(ch.location, "position_x", 0) if hasattr(ch, "location") else 0,
            "position_y": getattr(ch.location, "position_y", 0) if hasattr(ch, "location") else 0,
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
            d["functions"] = list(ch.functions) if hasattr(ch, "functions") and ch.functions else []
        out.append(d)
    return out
