"""Actor 仓储 / Actor Repository — 配对角色 CRUD 操作"""

from typing import Any

from ..domain import Actor
from ..storage.sqlite_client import SQLiteClient
from ..utils.tracing import traced


def _val(data: dict[str, Any], key: str, default: Any = None) -> Any:
    v = data.get(key)
    return default if v is None else v


# Actor CRUD / 配对角色增删改查
class ActorRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    @traced()
    async def save(self, actor: Actor) -> None:
        """保存/更新 Actor / Insert or update an actor."""
        await self._db.execute(
            """INSERT INTO actors (id, name, role, race, status, disposition, scene_id,
            position_x, position_y, attributes_json, combat_json, functions_json,
            function_data_json, inventory_json, relationships_json, dm_assigned,
            motivation_injected, world_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, disposition=excluded.disposition, scene_id=excluded.scene_id,
            position_x=excluded.position_x, position_y=excluded.position_y,
            dm_assigned=excluded.dm_assigned, motivation_injected=excluded.motivation_injected,
            world_id=excluded.world_id, updated_at=datetime('now', 'localtime')""",
            (
                actor.id,
                actor.name,
                actor.role,
                actor.race,
                actor.status,
                actor.disposition,
                actor.scene_id,
                actor.position_x,
                actor.position_y,
                actor.attributes_json,
                actor.combat_json,
                actor.functions_json,
                actor.function_data_json,
                actor.inventory_json,
                actor.relationships_json,
                int(actor.dm_assigned),
                actor.motivation_injected,
                actor.world_id,
            ),
        )
        await self._db.commit()

    @traced()
    async def load_all(self, world_id: str | None = None) -> list[Actor]:
        if world_id:
            rows = await self._db.fetch_all("SELECT * FROM actors WHERE world_id = ?", (world_id,))
        else:
            rows = await self._db.fetch_all("SELECT * FROM actors")
        return [_actor_from_row(r) for r in rows]

    @traced()
    async def load_one(self, actor_id: str) -> Actor | None:
        row = await self._db.fetch_one("SELECT * FROM actors WHERE id = ?", (actor_id,))
        return _actor_from_row(row) if row else None

    @traced()
    async def list_rows(self, world_id: str) -> list[dict]:
        return await self._db.fetch_all("SELECT * FROM actors WHERE world_id = ?", (world_id,))

    @traced()
    async def delete_by_world(self, world_id: str) -> None:
        """删除 world 下全部 Actor / Delete all actors in a world."""
        await self._db.execute("DELETE FROM actors WHERE world_id = ?", (world_id,))
        await self._db.commit()


def _actor_from_row(row: dict) -> Actor:
    return Actor(
        id=row["id"],
        name=row["name"],
        role=row["role"],
        race=_val(row, "race"),
        status=_val(row, "status", "active"),
        disposition=_val(row, "disposition", "neutral"),
        scene_id=_val(row, "scene_id", ""),
        position_x=_val(row, "position_x", 0),
        position_y=_val(row, "position_y", 0),
        attributes_json=_val(row, "attributes_json", "{}"),
        combat_json=_val(row, "combat_json", "{}"),
        dm_assigned=bool(_val(row, "dm_assigned", 0)),
        motivation_injected=_val(row, "motivation_injected"),
        world_id=_val(row, "world_id", ""),
    )
