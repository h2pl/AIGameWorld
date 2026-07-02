"""角色仓储 / Character Repository — 用 SQLiteClient，零 SQL."""

from typing import Any

from ..domain import Actor, PlayerCharacter
from ..storage.sqlite_client import SQLiteClient

# ── 辅助函数 / Helpers ──


def _val(data: dict[str, Any], key: str, default: Any = None) -> Any:
    v = data.get(key)
    return default if v is None else v


class CharacterRepo:
    """角色存取——PC + Actor."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    # ── 写 ──
    async def save_pc(self, pc: PlayerCharacter) -> None:
        await self._db.execute(
            """
            INSERT INTO player_characters (id, name, role, race, status, scene_id,
            position_x, position_y, attributes_json, combat_json, character_arc_json,
            values_json, equipment_json, inventory_json, relationships_json, world_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, scene_id=excluded.scene_id,
            position_x=excluded.position_x, position_y=excluded.position_y,
            world_id=excluded.world_id,
            updated_at=datetime('now')
        """,
            (
                pc.id,
                pc.name,
                pc.role,
                pc.race,
                pc.status,
                pc.scene_id,
                pc.position_x,
                pc.position_y,
                pc.attributes_json,
                pc.combat_json,
                pc.character_arc_json,
                pc.values_json,
                pc.equipment_json,
                pc.inventory_json,
                pc.relationships_json,
                pc.world_id,
            ),
        )

    async def save_actor(self, actor: Actor) -> None:
        await self._db.execute(
            """
            INSERT INTO actors (id, name, role, race, status, scene_id,
            position_x, position_y, attributes_json, combat_json, functions_json,
            function_data_json, inventory_json, relationships_json, dm_assigned,
            motivation_injected, world_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, scene_id=excluded.scene_id,
            position_x=excluded.position_x, position_y=excluded.position_y,
            dm_assigned=excluded.dm_assigned,
            motivation_injected=excluded.motivation_injected,
            world_id=excluded.world_id,
            updated_at=datetime('now')
        """,
            (
                actor.id,
                actor.name,
                actor.role,
                actor.race,
                actor.status,
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

    # ── 读 ──
    async def load_pcs(self, world_id: str | None = None) -> list[PlayerCharacter]:
        """加载 PC / Load PCs. world_id=None 加载全部."""
        if world_id:
            rows = await self._db.fetch_all(
                "SELECT * FROM player_characters WHERE world_id = ?", (world_id,)
            )
        else:
            rows = await self._db.fetch_all("SELECT * FROM player_characters")
        return [_pc_from_row(r) for r in rows]

    async def load_pc(self, char_id: str) -> PlayerCharacter | None:
        """按 ID 加载单个 PC / Load PC by ID."""
        row = await self._db.fetch_one("SELECT * FROM player_characters WHERE id = ?", (char_id,))
        return _pc_from_row(row) if row else None

    async def load_actors(self, world_id: str | None = None) -> list[Actor]:
        """加载 Actor / Load Actors. world_id=None 加载全部."""
        if world_id:
            rows = await self._db.fetch_all("SELECT * FROM actors WHERE world_id = ?", (world_id,))
        else:
            rows = await self._db.fetch_all("SELECT * FROM actors")
        return [_actor_from_row(r) for r in rows]

    async def load_actor(self, actor_id: str) -> Actor | None:
        """按 ID 加载单个 Actor / Load Actor by ID."""
        row = await self._db.fetch_one("SELECT * FROM actors WHERE id = ?", (actor_id,))
        return _actor_from_row(row) if row else None


# Row → Model
def _pc_from_row(row: dict) -> PlayerCharacter:
    return PlayerCharacter(
        id=row["id"],
        name=row["name"],
        role=row["role"],
        race=_val(row, "race"),
        status=_val(row, "status", "active"),
        scene_id=_val(row, "scene_id", ""),
        position_x=_val(row, "position_x", 0),
        position_y=_val(row, "position_y", 0),
        world_id=_val(row, "world_id", ""),
    )


def _actor_from_row(row: dict) -> Actor:
    return Actor(
        id=row["id"],
        name=row["name"],
        role=row["role"],
        race=_val(row, "race"),
        status=_val(row, "status", "active"),
        scene_id=_val(row, "scene_id", ""),
        position_x=_val(row, "position_x", 0),
        position_y=_val(row, "position_y", 0),
        dm_assigned=bool(_val(row, "dm_assigned", 0)),
        motivation_injected=_val(row, "motivation_injected"),
        world_id=_val(row, "world_id", ""),
    )
