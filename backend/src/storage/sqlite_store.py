"""WorldStateStore — SQLite 世界状态持久化 / SQLite world state persistence.

基于 docs/06-data-layer.md §7 / Based on docs/06-data-layer.md §7.
"""

import json
from pathlib import Path

import aiosqlite

from src.models import (
    Actor, Attributes, CharacterArc, CombatStats, Equipment, Event,
    InventorySlot, Item, ItemType, Location, MainCastRoster,
    PlayerCharacter, Relationship, Scene, SceneObject, SceneObjectType,
    StoryArc, StoryHook, WorldState,
)
from src.models.story import CastChangeEvent


# ---- 工具函数 / Utilities ----

def _row_val(row, key, default=None):
    """安全访问 aiosqlite.Row（不支持 .get()）/ Safe row accessor for aiosqlite.Row.
    将 SQL NULL 转换为提供的默认值 / Converts SQL NULL to the provided default."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, IndexError):
        return default


# ---- 世界状态存储 / World State Store ----

class WorldStateStore:
    """SQLite 世界状态持久化 / SQLite-backed world state persistence.
    设计原则 / Design principles:
    - 异步 aiosqlite / Async aiosqlite
    - save_tick 单事务保证原子性 / Single-transaction atomicity
    - models/ 与 storage/ 分离 / Separation of models and IO
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    # ---- 生命周期 / Lifecycle ----

    async def init(self) -> None:
        """建库 + 执行 schema.sql / Create DB + run schema.sql. 启动时调用一次 / Call once at startup."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        await self._db.executescript(schema)
        await self._db.commit()

    async def close(self) -> None:
        """关闭数据库连接 / Close DB connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ---- 聚合读写 / Aggregation ----

    async def load_world_state(self) -> WorldState:
        """启动时从 SQLite 组装完整 WorldState / Assemble full WorldState from SQLite at startup."""
        meta = await self._load_meta()
        return WorldState(
            tick=meta.get("tick", 0),
            current_world=meta.get("current_world", ""),
            current_scene=meta.get("current_scene", ""),
            scenes=await self._load_scenes(),
            player_characters=await self._load_player_characters(),
            actors=await self._load_actors(),
            scene_objects=await self._load_scene_objects(),
            items=await self._load_items(),
            story_arcs=await self._load_story_arcs(),
            story_hooks=await self._load_story_hooks(),
            main_cast=await self._load_main_cast(),
        )

    async def save_tick(
        self, state: WorldState, new_events: list[Event], narrative: str | None = None
    ) -> None:
        """每 Tick 持久化：PC/Actor + Event + 叙事 + tick / Persist after a tick.
        单事务保证原子性 / Single transaction ensures atomicity."""
        async with self._db.execute("BEGIN"):
            for pc in state.player_characters.values():
                await self._upsert_pc(pc)
            for actor in state.actors.values():
                await self._upsert_actor(actor)
            for evt in new_events:
                await self._insert_event(evt)
            if narrative:
                await self._db.execute(
                    "INSERT INTO narratives (tick, content) VALUES (?, ?)",
                    (state.tick, narrative),
                )
            await self._db.execute(
                "INSERT OR REPLACE INTO world_meta (key, value) VALUES ('tick', ?)",
                (str(state.tick),),
            )
            await self._db.commit()

    # ============ 私有加载器 / Private Loaders ============

    async def _load_meta(self) -> dict:
        rows = await self._db.execute_fetchall("SELECT key, value FROM world_meta")
        result = {}
        for row in rows:
            k, v = row[0], row[1]
            result[k] = int(v) if k == "tick" else v
        return result

    async def _load_scenes(self) -> dict[str, Scene]:
        rows = await self._db.execute_fetchall("SELECT * FROM scenes")
        return {
            row["id"]: Scene(
                id=row["id"], name=row["name"], type=row["type"],
                description=_row_val(row, "description", ""),
                exits=json.loads(_row_val(row, "exits_json", "[]")),
                landmarks=json.loads(_row_val(row, "landmarks_json", "[]")),
                environment=json.loads(_row_val(row, "environment_json", "{}")),
                pack_name=row["pack_name"],
            )
            for row in rows
        }

    async def _load_player_characters(self) -> dict[str, PlayerCharacter]:
        rows = await self._db.execute_fetchall("SELECT * FROM player_characters")
        return {row["id"]: _pc_from_row(row) for row in rows}

    async def _load_actors(self) -> dict[str, Actor]:
        rows = await self._db.execute_fetchall("SELECT * FROM actors")
        return {row["id"]: _actor_from_row(row) for row in rows}

    async def _load_items(self) -> dict[str, Item]:
        rows = await self._db.execute_fetchall("SELECT * FROM items")
        return {row["id"]: _item_from_row(row) for row in rows}

    async def _load_scene_objects(self) -> dict[str, SceneObject]:
        rows = await self._db.execute_fetchall("SELECT * FROM scene_objects")
        return {row["id"]: _scene_object_from_row(row) for row in rows}

    async def _load_story_arcs(self) -> list[StoryArc]:
        rows = await self._db.execute_fetchall("SELECT * FROM story_arcs")
        return [
            StoryArc(
                id=row["id"], type=row["type"], title=row["title"],
                stage=_row_val(row, "stage", ""),
                main_cast=json.loads(_row_val(row, "main_cast_json", "[]")),
                supporting_actors=json.loads(_row_val(row, "supporting_actors_json", "[]")),
                key_event_ticks=json.loads(_row_val(row, "key_event_ticks_json", "[]")),
                branching_points=json.loads(_row_val(row, "branching_points_json", "[]")),
                status=_row_val(row, "status", "setup"),
            )
            for row in rows
        ]

    async def _load_story_hooks(self) -> list[StoryHook]:
        rows = await self._db.execute_fetchall("SELECT * FROM story_hooks")
        return [
            StoryHook(
                id=row["id"], planted_tick=row["planted_tick"],
                description=_row_val(row, "description", ""),
                intended_payoff=_row_val(row, "intended_payoff", ""),
                urgency=_row_val(row, "urgency", 10),
                status=_row_val(row, "status", "planted"),
            )
            for row in rows
        ]

    async def _load_main_cast(self) -> MainCastRoster:
        rows = await self._db.execute_fetchall("SELECT * FROM main_cast ORDER BY tick")
        return MainCastRoster(
            current_members=[],
            history=[
                CastChangeEvent(
                    tick=row["tick"], character_id=row["character_id"],
                    event_type=row["event_type"],
                    reason=_row_val(row, "reason", ""),
                    arc_id=_row_val(row, "arc_id"),
                )
                for row in rows
            ],
        )

    # ============ UPSERT 操作 / UPSERT Operations ============

    async def _upsert_pc(self, pc: PlayerCharacter) -> None:
        """PC 增量持久化（位置/HP/关系/importance）/ Upsert PC with changed fields."""
        params = (
            pc.id, pc.name, pc.role, pc.race, pc.status,
            pc.location.scene_id, pc.location.position_x, pc.location.position_y,
            pc.attributes.model_dump_json(by_alias=True),  # 用别名输出 "str"/"dex" 等
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
        )
        await self._db.execute(
            """INSERT INTO player_characters (id, name, role, race, status, scene_id,
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
               updated_at=datetime('now')""",
            params,
        )

    async def _upsert_actor(self, actor: Actor) -> None:
        """Actor 增量持久化（位置/战斗/动机/功能）/ Upsert Actor with changed fields."""
        params = (
            actor.id, actor.name, actor.role, actor.race, actor.status,
            actor.location.scene_id, actor.location.position_x, actor.location.position_y,
            actor.attributes.model_dump_json(by_alias=True),
            actor.combat.model_dump_json() if actor.combat else None,
            actor.personality,
            json.dumps([f.value for f in actor.functions]),
            json.dumps(actor.function_data),
            actor.equipment.model_dump_json() if actor.equipment else None,
            json.dumps([s.model_dump() for s in actor.inventory]),
            actor.memory_count, actor.importance_accumulator,
            json.dumps({k: v.model_dump() for k, v in actor.relationships.items()}),
            int(actor.dm_assigned), actor.motivation_injected,
            json.dumps(actor.service_arcs),
        )
        await self._db.execute(
            """INSERT INTO actors (id, name, role, race, status, scene_id,
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
               updated_at=datetime('now')""",
            params,
        )

    async def _insert_event(self, evt: Event) -> None:
        """追加事件（Event Log 只追加不修改）/ Append event (immutable log)."""
        await self._db.execute(
            "INSERT INTO events (id, tick, seq, type, importance, source, target, data_json, narrative) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (evt.id, evt.tick, evt.seq, evt.type, evt.importance,
             evt.source, evt.target, json.dumps(evt.data), evt.narrative),
        )


# ============ Row → Model 转换器 / Row-to-Model Converters ============

def _pc_from_row(row: aiosqlite.Row) -> PlayerCharacter:
    """SQLite 行 → PlayerCharacter / Convert SQLite row to PlayerCharacter."""
    return PlayerCharacter(
        id=row["id"], name=row["name"], role=row["role"],
        race=_row_val(row, "race"),
        status=_row_val(row, "status", "active"),
        location=Location(
            scene_id=row["scene_id"],
            position_x=_row_val(row, "position_x", 0),
            position_y=_row_val(row, "position_y", 0),
        ),
        attributes=Attributes.model_validate_json(row["attributes_json"]),
        combat=CombatStats.model_validate_json(row["combat_json"]),
        character_arc=CharacterArc.model_validate_json(row["character_arc_json"]),
        long_term_goal=_row_val(row, "long_term_goal", ""),
        values=json.loads(_row_val(row, "values_json", "[]")),
        personality=_row_val(row, "personality", ""),
        equipment=Equipment.model_validate_json(row["equipment_json"]),
        inventory=[InventorySlot(**i) for i in json.loads(row["inventory_json"])],
        memory_count=_row_val(row, "memory_count", 0),
        importance_accumulator=_row_val(row, "importance_accumulator", 0.0),
        relationships={
            k: Relationship(**v)
            for k, v in json.loads(_row_val(row, "relationships_json", "{}")).items()
        },
        joined_tick=_row_val(row, "joined_tick", 0),
        roster_status=_row_val(row, "roster_status", "member"),
    )


def _actor_from_row(row: aiosqlite.Row) -> Actor:
    """SQLite 行 → Actor / Convert SQLite row to Actor."""
    combat_json = _row_val(row, "combat_json")
    equipment_json = _row_val(row, "equipment_json")
    return Actor(
        id=row["id"], name=row["name"], role=row["role"],
        race=_row_val(row, "race"),
        status=_row_val(row, "status", "active"),
        location=Location(
            scene_id=row["scene_id"],
            position_x=_row_val(row, "position_x", 0),
            position_y=_row_val(row, "position_y", 0),
        ),
        attributes=Attributes.model_validate_json(row["attributes_json"]),
        combat=CombatStats.model_validate_json(combat_json) if combat_json else None,
        personality=_row_val(row, "personality", ""),
        functions=[f for f in json.loads(row["functions_json"])],
        function_data=json.loads(row["function_data_json"]),
        equipment=Equipment.model_validate_json(equipment_json) if equipment_json else None,
        inventory=[InventorySlot(**i) for i in json.loads(row["inventory_json"])],
        memory_count=_row_val(row, "memory_count", 0),
        importance_accumulator=_row_val(row, "importance_accumulator", 0.0),
        relationships={
            k: Relationship(**v)
            for k, v in json.loads(_row_val(row, "relationships_json", "{}")).items()
        },
        dm_assigned=bool(_row_val(row, "dm_assigned", 0)),
        motivation_injected=_row_val(row, "motivation_injected"),
        service_arcs=json.loads(_row_val(row, "service_arcs_json", "[]")),
    )


def _item_from_row(row: aiosqlite.Row) -> Item:
    """SQLite 行 → Item / Convert SQLite row to Item."""
    return Item(
        id=row["id"], name=row["name"],
        item_type=ItemType(row["item_type"]),
        rarity=_row_val(row, "rarity", "common"),
        weight=_row_val(row, "weight", 0.0),
        value=_row_val(row, "value", 0),
        description=_row_val(row, "description", ""),
        data=json.loads(_row_val(row, "data_json", "{}")),
        pack_name=row["pack_name"],
    )


def _scene_object_from_row(row: aiosqlite.Row) -> SceneObject:
    """SQLite 行 → SceneObject / Convert SQLite row to SceneObject."""
    int_data = _row_val(row, "interact_data_json")
    return SceneObject(
        id=row["id"], name=row["name"],
        object_type=SceneObjectType(row["object_type"]),
        scene_id=row["scene_id"],
        position_x=_row_val(row, "position_x", 0),
        position_y=_row_val(row, "position_y", 0),
        interactable=bool(_row_val(row, "interactable", 1)),
        interact_data=json.loads(int_data) if int_data else None,
    )
