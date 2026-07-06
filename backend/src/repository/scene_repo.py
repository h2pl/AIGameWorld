"""场景仓储 / Scene Repository."""

import json

from ..domain import SceneObject, SceneObjectType
from ..storage.sqlite_client import SQLiteClient


class SceneRepo:
    """场景对象存取——读全部 + 写单条 + 写场景."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    async def list_scenes(self, world_id: str) -> list[dict]:
        """按 world_id 加载场景摘要列表."""
        rows = await self._db.fetch_all(
            "SELECT id, name, type, description, map_key, spawn_x, spawn_y, map_width, map_height, ext_json FROM scenes WHERE world_id = ?",
            (world_id,),
        )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "description": r["description"],
                "map_key": r.get("map_key", ""),
                "spawn_x": r.get("spawn_x", 0),
                "spawn_y": r.get("spawn_y", 0),
                "map_width": r.get("map_width", 40),
                "map_height": r.get("map_height", 40),
                "ext_json": r.get("ext_json", "{}"),
            }
            for r in rows
        ]

    async def get_scene(self, scene_id: str) -> dict | None:
        """按 scene_id 加载单个场景."""
        row = await self._db.fetch_one(
            "SELECT id, name, type, description, map_key, spawn_x, spawn_y, map_width, map_height, ext_json FROM scenes WHERE id = ?",
            (scene_id,),
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "description": row["description"],
            "map_key": row.get("map_key", ""),
            "spawn_x": row.get("spawn_x", 0),
            "spawn_y": row.get("spawn_y", 0),
            "map_width": row.get("map_width", 40),
            "map_height": row.get("map_height", 40),
            "ext_json": row.get("ext_json", "{}"),
        }

    async def get_object_ids(self, scene_id: str) -> list[str]:
        """按 scene_id 获取关联的场景对象 id 列表."""
        rows = await self._db.fetch_all(
            "SELECT id FROM scene_objects WHERE scene_id = ?", (scene_id,)
        )
        return [r["id"] for r in rows]

    async def save_scene(self, scene: dict, world_id: str) -> None:
        """写入单条场景."""
        await self._db.execute(
            "INSERT OR REPLACE INTO scenes "
            "(id, name, type, description, map_key, spawn_x, spawn_y, map_width, map_height, ext_json, world_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))",
            (
                scene.get("id", ""),
                scene.get("name", ""),
                scene.get("type", ""),
                scene.get("description", ""),
                scene.get("map_key", ""),
                scene.get("spawn_x", 0),
                scene.get("spawn_y", 0),
                scene.get("map_width", 40),
                scene.get("map_height", 40),
                scene.get("ext_json", "{}"),
                world_id,
            ),
        )
        await self._db.commit()

    async def save_object(self, obj: SceneObject) -> None:
        """写入单条场景对象."""
        await self._db.execute(
            "INSERT OR REPLACE INTO scene_objects "
            "(id, name, object_type, scene_id, position_x, position_y, interactable, interact_data, world_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))",
            (
                obj.id,
                obj.name,
                obj.object_type.value,
                obj.scene_id,
                obj.position_x,
                obj.position_y,
                int(obj.interactable),
                json.dumps(obj.interact_data, ensure_ascii=False) if obj.interact_data else None,
                obj.world_id,
            ),
        )
        await self._db.commit()

    async def list_objects_by_world(self, world_id: str) -> list[dict]:
        """按 world_id 加载场景物体列表 / List scene objects by world."""
        rows = await self._db.fetch_all(
            "SELECT id, name, object_type, scene_id, position_x, position_y FROM scene_objects WHERE world_id = ?",
            (world_id,),
        )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "object_type": r["object_type"],
                "scene_id": r["scene_id"],
                "position_x": r.get("position_x", 0),
                "position_y": r.get("position_y", 0),
            }
            for r in rows
        ]

    async def delete_by_world(self, world_id: str) -> None:
        """删除指定 world 下所有场景及场景对象 / Delete all scenes and objects for a world."""
        await self._db.execute("DELETE FROM scene_objects WHERE world_id = ?", (world_id,))
        await self._db.execute("DELETE FROM scenes WHERE world_id = ?", (world_id,))
        await self._db.commit()

    async def load_all(self) -> dict[str, SceneObject]:
        """加载全部场景对象."""
        rows = await self._db.fetch_all("SELECT * FROM scene_objects")
        result = {}
        for r in rows:
            idata = r.get("interact_data")
            result[r["id"]] = SceneObject(
                id=r["id"],
                name=r["name"],
                object_type=SceneObjectType(r["object_type"]),
                scene_id=r["scene_id"],
                position_x=r.get("position_x", 0),
                position_y=r.get("position_y", 0),
                interactable=bool(r.get("interactable", 1)),
                interact_data=json.loads(idata) if idata else None,
                world_id=r.get("world_id", ""),
            )
        return result
