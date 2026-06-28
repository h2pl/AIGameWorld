"""故事仓储."""

import json

from ..domain import StoryArc, StoryHook, CastChangeEvent, MainCastRoster
from ..storage.sqlite_client import SQLiteClient


class StoryRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def load_arcs(self) -> list[StoryArc]:
        rows = await self._db.fetch_all("SELECT * FROM story_arcs")
        return [StoryArc(
            id=r["id"], type=r["type"], title=r["title"],
            stage=r.get("stage", ""),
            main_cast=json.loads(r.get("main_cast_json", "[]")),
            supporting_actors=json.loads(r.get("supporting_actors_json", "[]")),
            key_event_ticks=json.loads(r.get("key_event_ticks_json", "[]")),
            branching_points=json.loads(r.get("branching_points_json", "[]")),
            status=r.get("status", "setup"),
        ) for r in rows]

    async def save_arc(self, arc: StoryArc) -> None:
        await self._db.execute("""
            INSERT OR REPLACE INTO story_arcs
            (id, type, title, stage, main_cast_json, supporting_actors_json,
             key_event_ticks_json, branching_points_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (arc.id, arc.type, arc.title, arc.stage,
              json.dumps(arc.main_cast), json.dumps(arc.supporting_actors),
              json.dumps(arc.key_event_ticks), json.dumps([bp.model_dump() for bp in arc.branching_points]),
              arc.status))

    async def load_hooks(self) -> list[StoryHook]:
        rows = await self._db.fetch_all("SELECT * FROM story_hooks")
        return [StoryHook(
            id=r["id"], planted_tick=r["planted_tick"],
            description=r.get("description", ""),
            intended_payoff=r.get("intended_payoff", ""),
            urgency=r.get("urgency", 10), status=r.get("status", "planted"),
        ) for r in rows]

    async def save_hook(self, hook: StoryHook) -> None:
        await self._db.execute("""
            INSERT OR REPLACE INTO story_hooks
            (id, planted_tick, description, intended_payoff, urgency, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (hook.id, hook.planted_tick, hook.description, hook.intended_payoff, hook.urgency, hook.status))

    async def load_cast(self) -> MainCastRoster:
        rows = await self._db.fetch_all("SELECT * FROM main_cast ORDER BY tick")
        return MainCastRoster(history=[CastChangeEvent(
            tick=r["tick"], character_id=r["character_id"],
            event_type=r["event_type"], reason=r.get("reason", ""), arc_id=r.get("arc_id"),
        ) for r in rows])

    async def insert_narrative(self, tick: int, content: str) -> None:
        await self._db.execute("INSERT INTO narratives (tick, content) VALUES (?, ?)", (tick, content))
