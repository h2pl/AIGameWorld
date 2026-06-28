"""角色仓储 / Character Repository — 用 SQLiteClient，零 SQL."""

import json
from typing import Any

from ..domain import PlayerCharacter, Actor, Location, Attributes, CombatStats, Equipment, InventorySlot, Relationship, CharacterArc
from ..storage.sqlite_client import SQLiteClient


def _val(data: dict[str, Any], key: str, default: Any = None) -> Any:
    v = data.get(key)
    return default if v is None else v


class CharacterRepo:
    """角色存取——PC + Actor."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    # ── 写 ──
    async def save_pc(self, pc: PlayerCharacter) -> None:
        await self._db.execute("""
            INSERT INTO player_characters (id, name, role, race, status, scene_id,
            position_x, position_y, attributes_json, combat_json,
            character_arc_json, long_term_goal, values_json,
            personality, equipment_json, inventory_json,
            memory_count, importance_accumulator, relationships_json,
            joined_tick, roster_status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, scene_id=excluded.scene_id,
            position_x=excluded.position_x, position_y=excluded.position_y,
            combat_json=excluded.combat_json, equipment_json=excluded.equipment_json,
            inventory_json=excluded.inventory_json,
            memory_count=excluded.memory_count,
            importance_accumulator=excluded.importance_accumulator,
            relationships_json=excluded.relationships_json,
            updated_at=datetime('now')
        """, (
            pc.id, pc.name, pc.role, pc.race, pc.status,
            pc.location.scene_id, pc.location.position_x, pc.location.position_y,
            pc.attributes.model_dump_json(by_alias=True),
            pc.combat.model_dump_json(),
            pc.character_arc.model_dump_json(),
            pc.long_term_goal,
            json.dumps(pc.values),
            pc.personality,
            pc.equipment.model_dump_json(),
            json.dumps([s.model_dump() for s in pc.inventory]),
            pc.memory_count, pc.importance_accumulator,
            json.dumps({k: v.model_dump() for k, v in pc.relationships.items()}),
            pc.joined_tick, pc.roster_status,
        ))

    async def save_actor(self, actor: Actor) -> None:
        await self._db.execute("""
            INSERT INTO actors (id, name, role, race, status, scene_id,
            position_x, position_y, attributes_json, combat_json,
            personality, functions_json, function_data_json,
            equipment_json, inventory_json,
            memory_count, importance_accumulator, relationships_json,
            dm_assigned, motivation_injected, service_arcs_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, scene_id=excluded.scene_id,
            position_x=excluded.position_x, position_y=excluded.position_y,
            combat_json=excluded.combat_json, equipment_json=excluded.equipment_json,
            inventory_json=excluded.inventory_json,
            memory_count=excluded.memory_count,
            importance_accumulator=excluded.importance_accumulator,
            relationships_json=excluded.relationships_json,
            dm_assigned=excluded.dm_assigned,
            motivation_injected=excluded.motivation_injected,
            updated_at=datetime('now')
        """, (
            actor.id, actor.name, actor.role, actor.race, actor.status,
            actor.location.scene_id, actor.location.position_x, actor.location.position_y,
            actor.attributes.model_dump_json(by_alias=True),
            actor.combat.model_dump_json() if actor.combat else None,
            actor.personality,
            json.dumps([f for f in actor.functions]),
            json.dumps(actor.function_data),
            actor.equipment.model_dump_json() if actor.equipment else None,
            json.dumps([s.model_dump() for s in actor.inventory]),
            actor.memory_count, actor.importance_accumulator,
            json.dumps({k: v.model_dump() for k, v in actor.relationships.items()}),
            int(actor.dm_assigned), actor.motivation_injected,
            json.dumps(actor.service_arcs),
        ))

    # ── 读 ──
    async def load_pcs(self) -> list[PlayerCharacter]:
        rows = await self._db.fetch_all("SELECT * FROM player_characters")
        return [_pc_from_row(r) for r in rows]

    async def load_actors(self) -> list[Actor]:
        rows = await self._db.fetch_all("SELECT * FROM actors")
        return [_actor_from_row(r) for r in rows]


# Row → Model
def _pc_from_row(row: dict) -> PlayerCharacter:
    return PlayerCharacter(
        id=row["id"], name=row["name"], role=row["role"],
        race=_val(row, "race"),
        status=_val(row, "status", "active"),
        location=Location(scene_id=row["scene_id"], position_x=_val(row, "position_x", 0), position_y=_val(row, "position_y", 0)),
        attributes=Attributes.model_validate_json(row["attributes_json"]),
        combat=CombatStats.model_validate_json(row["combat_json"]),
        character_arc=CharacterArc.model_validate_json(row["character_arc_json"]),
        long_term_goal=_val(row, "long_term_goal", ""),
        values=json.loads(_val(row, "values_json", "[]")),
        personality=_val(row, "personality", ""),
        equipment=Equipment.model_validate_json(row["equipment_json"]),
        inventory=[InventorySlot(**i) for i in json.loads(row["inventory_json"])],
        memory_count=_val(row, "memory_count", 0),
        importance_accumulator=_val(row, "importance_accumulator", 0.0),
        relationships={k: Relationship(**v) for k, v in json.loads(_val(row, "relationships_json", "{}")).items()},
        joined_tick=_val(row, "joined_tick", 0),
        roster_status=_val(row, "roster_status", "member"),
    )


def _actor_from_row(row: dict) -> Actor:
    cj = _val(row, "combat_json")
    ej = _val(row, "equipment_json")
    return Actor(
        id=row["id"], name=row["name"], role=row["role"],
        race=_val(row, "race"), status=_val(row, "status", "active"),
        location=Location(scene_id=row["scene_id"], position_x=_val(row, "position_x", 0), position_y=_val(row, "position_y", 0)),
        attributes=Attributes.model_validate_json(row["attributes_json"]),
        combat=CombatStats.model_validate_json(cj) if cj else None,
        personality=_val(row, "personality", ""),
        functions=[f for f in json.loads(row["functions_json"])],
        function_data=json.loads(row["function_data_json"]),
        equipment=Equipment.model_validate_json(ej) if ej else None,
        inventory=[InventorySlot(**i) for i in json.loads(row["inventory_json"])],
        memory_count=_val(row, "memory_count", 0),
        importance_accumulator=_val(row, "importance_accumulator", 0.0),
        relationships={k: Relationship(**v) for k, v in json.loads(_val(row, "relationships_json", "{}")).items()},
        dm_assigned=bool(_val(row, "dm_assigned", 0)),
        motivation_injected=_val(row, "motivation_injected"),
        service_arcs=json.loads(_val(row, "service_arcs_json", "[]")),
    )
