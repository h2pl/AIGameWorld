"""SQLite 实现 CharacterRepo——用 storage/sqlite_client 做裸 DB，自身只做 PC/Actor 存取."""

import json

from ..domain import PC, Actor
from ..storage.sqlite_client import SQLiteClient
from .world_state_repo import CharacterRepo


class SQLiteCharacterRepo(CharacterRepo):
    """PC/Actor 领域实体存取。不写 connect/execute，调 SQLiteClient."""

    def __init__(self, client: SQLiteClient | None = None):
        self._client = client or SQLiteClient()

    async def init(self) -> None:
        await self._client.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                character_type TEXT NOT NULL,
                data_json TEXT NOT NULL
            )
        """)

    # ── PC ──
    async def save_pc(self, pc: PC) -> None:
        await self._client.execute(
            "INSERT OR REPLACE INTO characters (id, character_type, data_json) VALUES (?, ?, ?)",
            pc.id, "pc", pc.model_dump_json(),
        )

    async def find_pc(self, character_id: str) -> PC | None:
        row = await self._client.fetch_one(
            "SELECT data_json FROM characters WHERE id = ? AND character_type = 'pc'",
            character_id,
        )
        return PC(**json.loads(row[0])) if row else None

    async def find_all_pcs(self) -> list[PC]:
        rows = await self._client.fetch_all(
            "SELECT data_json FROM characters WHERE character_type = 'pc'",
        )
        return [PC(**json.loads(r[0])) for r in rows]

    # ── Actor ──
    async def save_actor(self, actor: Actor) -> None:
        await self._client.execute(
            "INSERT OR REPLACE INTO characters (id, character_type, data_json) VALUES (?, ?, ?)",
            actor.id, "actor", actor.model_dump_json(),
        )

    async def find_actor(self, character_id: str) -> Actor | None:
        row = await self._client.fetch_one(
            "SELECT data_json FROM characters WHERE id = ? AND character_type = 'actor'",
            character_id,
        )
        return Actor(**json.loads(row[0])) if row else None

    async def find_all_actors(self) -> list[Actor]:
        rows = await self._client.fetch_all(
            "SELECT data_json FROM characters WHERE character_type = 'actor'",
        )
        return [Actor(**json.loads(r[0])) for r in rows]
