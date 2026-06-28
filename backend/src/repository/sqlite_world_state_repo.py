"""SQLiteCharacterRepo —— 实现 CharacterRepo，内部调 storage，零 SQL."""

from ..domain import PC, Actor
from ..storage.sqlite_client import SQLiteClient
from .world_state_repo import CharacterRepo


class SQLiteCharacterRepo(CharacterRepo):
    """零 SQL。只做领域模型 ↔ storage 的转换."""

    def __init__(self, client: SQLiteClient | None = None):
        self._client = client or SQLiteClient()

    async def init(self) -> None:
        await self._client.create_character_table()

    # ── PC ──
    async def save_pc(self, pc: PC) -> None:
        await self._client.insert_character(pc.id, "pc", pc.model_dump())

    async def find_pc(self, character_id: str) -> PC | None:
        data = await self._client.find_character(character_id, "pc")
        return PC(**data) if data else None

    async def find_all_pcs(self) -> list[PC]:
        rows = await self._client.find_all_characters("pc")
        return [PC(**r) for r in rows]

    # ── Actor ──
    async def save_actor(self, actor: Actor) -> None:
        await self._client.insert_character(actor.id, "actor", actor.model_dump())

    async def find_actor(self, character_id: str) -> Actor | None:
        data = await self._client.find_character(character_id, "actor")
        return Actor(**data) if data else None

    async def find_all_actors(self) -> list[Actor]:
        rows = await self._client.find_all_characters("actor")
        return [Actor(**r) for r in rows]
