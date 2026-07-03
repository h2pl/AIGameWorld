"""World CRUD + tick 管理."""

from ..domain.world import World
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class WorldRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def create(self, w: World) -> None:
        await self._db.execute(
            "INSERT INTO worlds (id, name, description, version, rule_set, author, starting_scene, current_tick) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                w.id,
                w.name,
                w.description,
                w.version,
                w.rule_set,
                w.author,
                w.starting_scene,
                w.current_tick,
            ),
        )
        await self._db.commit()
        logger.info("[repo] create id=%s", w.id)

    async def get(self, world_id: str) -> World | None:
        row = await self._db.fetch_one(
            "SELECT id, name, description, version, rule_set, author, starting_scene, current_tick "
            "FROM worlds WHERE id = ?",
            (world_id,),
        )
        return _row_to_world(row) if row else None

    async def list_all(self) -> list[World]:
        rows = await self._db.fetch_all(
            "SELECT id, name, description, version, rule_set, author, starting_scene, current_tick FROM worlds"
        )
        return [_row_to_world(r) for r in rows]

    async def get_tick(self, world_id: str) -> int:
        """获取当前 tick，world 不存在返回 0."""
        row = await self._db.fetch_one(
            "SELECT current_tick FROM worlds WHERE id = ?",
            (world_id,),
        )
        return row["current_tick"] if row else 0

    async def increment_tick(self, world_id: str) -> int:
        """tick+1 并返回新值."""
        await self._db.execute(
            "UPDATE worlds SET current_tick = current_tick + 1 WHERE id = ?",
            (world_id,),
        )
        await self._db.commit()
        row = await self._db.fetch_one(
            "SELECT current_tick FROM worlds WHERE id = ?",
            (world_id,),
        )
        return row["current_tick"] if row else 0

    async def reset_tick(self, world_id: str) -> None:
        """重置 tick 为 0."""
        await self._db.execute(
            "UPDATE worlds SET current_tick = 0 WHERE id = ?",
            (world_id,),
        )
        await self._db.commit()


def _row_to_world(row: dict) -> World:
    return World(
        id=row["id"],
        name=row["name"],
        description=row.get("description", ""),
        version=row.get("version", "1.0.0"),
        rule_set=row.get("rule_set", "dnd_5e_srd"),
        author=row.get("author", ""),
        starting_scene=row.get("starting_scene", ""),
        current_tick=row.get("current_tick", 0),
    )
