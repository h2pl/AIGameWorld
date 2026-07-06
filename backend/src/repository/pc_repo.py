"""PC 仓储 / Player Character Repository — 主角团 CRUD 操作"""

from typing import Any

from ..domain import PlayerCharacter
from ..storage.sqlite_client import SQLiteClient


def _val(data: dict[str, Any], key: str, default: Any = None) -> Any:
    v = data.get(key)
    return default if v is None else v


# PC CRUD / 主角团增删改查
class PcRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def save(self, pc: PlayerCharacter) -> None:
        await self._db.execute(
            """INSERT INTO player_characters (id, name, role, race, status, scene_id,
            position_x, position_y, attributes_json, combat_json, arc_json,
            values_json, equipment_json, inventory_json, relationships_json, world_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, scene_id=excluded.scene_id,
            position_x=excluded.position_x, position_y=excluded.position_y,
            world_id=excluded.world_id, updated_at=datetime('now', 'localtime')""",
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
                pc.arc_json,
                pc.values_json,
                pc.equipment_json,
                pc.inventory_json,
                pc.relationships_json,
                pc.world_id,
            ),
        )
        await self._db.commit()

    async def load_all(self, world_id: str | None = None) -> list[PlayerCharacter]:
        if world_id:
            rows = await self._db.fetch_all(
                "SELECT * FROM player_characters WHERE world_id = ?", (world_id,)
            )
        else:
            rows = await self._db.fetch_all("SELECT * FROM player_characters")
        return [_pc_from_row(r) for r in rows]

    async def load_one(self, pc_id: str) -> PlayerCharacter | None:
        row = await self._db.fetch_one("SELECT * FROM player_characters WHERE id = ?", (pc_id,))
        return _pc_from_row(row) if row else None

    async def list_rows(self, world_id: str) -> list[dict]:
        return await self._db.fetch_all(
            "SELECT * FROM player_characters WHERE world_id = ?", (world_id,)
        )

    async def reset_positions(self, world_id: str) -> None:
        await self._db.execute(
            "UPDATE player_characters SET position_x = 0, position_y = 0, updated_at = datetime('now', 'localtime') WHERE world_id = ?",
            (world_id,),
        )
        await self._db.commit()

    async def delete_by_world(self, world_id: str) -> None:
        await self._db.execute("DELETE FROM player_characters WHERE world_id = ?", (world_id,))
        await self._db.commit()


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
        attributes_json=_val(row, "attributes_json", "{}"),
        combat_json=_val(row, "combat_json", "{}"),
        world_id=_val(row, "world_id", ""),
    )
