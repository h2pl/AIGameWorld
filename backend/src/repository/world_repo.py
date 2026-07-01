"""World CRUD——worlds 表读写 / World repository: create, list."""

from ..domain.world import World
from ..storage.sqlite_client import SQLiteClient


class WorldRepo:
    """World 持久化 / World persistence."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    # 创建世界 / Create world
    async def create(self, w: World) -> None:
        await self._db.execute(
            "INSERT INTO worlds (id, name, pack_id, description) VALUES (?, ?, ?, ?)",
            (w.id, w.name, w.pack_id, w.description),
        )
        await self._db.commit()

    async def list_all(self) -> list[World]:
        rows = await self._db.fetch_all("SELECT id, name, pack_id, description FROM worlds")
        return [
            World(
                id=r["id"],
                name=r["name"],
                pack_id=r["pack_id"],
                description=r.get("description", ""),
            )
            for r in rows
        ]
