"""World CRUD——worlds 表读写 / World repository: create, list."""

import logging

from ..domain.world import World
from ..storage.sqlite_client import SQLiteClient

logger = logging.getLogger("aw.repo.world")


class WorldRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def create(self, w: World) -> None:
        await self._db.execute(
            "INSERT INTO worlds (id, name, description, version, rule_set, author, starting_scene) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (w.id, w.name, w.description, w.version, w.rule_set, w.author, w.starting_scene),
        )
        await self._db.commit()
        logger.info("[world] create id=%s name=%s", w.id, w.name)

    async def list_all(self) -> list[World]:
        rows = await self._db.fetch_all(
            "SELECT id, name, description, version, rule_set, author, starting_scene FROM worlds"
        )
        return [
            World(
                id=r["id"],
                name=r["name"],
                description=r.get("description", ""),
                version=r.get("version", "1.0.0"),
                rule_set=r.get("rule_set", "dnd_5e_srd"),
                author=r.get("author", ""),
                starting_scene=r.get("starting_scene", ""),
            )
            for r in rows
        ]
