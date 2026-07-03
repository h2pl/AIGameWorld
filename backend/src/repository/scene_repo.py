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
            "SELECT id, name, type, description FROM scenes WHERE world_id = ?", (world_id,)
        )
        return [
            {"id": r["id"], "name": r["name"], "type": r["type"], "description": r["description"]}
            for r in rows
        ]

    async def get_scene(self, scene_id: str) -> dict | None:
        """按 scene_id 加载单个场景."""
        row = await self._db.fetch_one(
            "SELECT id, name, type, description FROM scenes WHERE id = ?",
            (scene_id,),
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "description": row["description"],
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
            "INSERT OR REPLACE INTO scenes (id, name, type, description, world_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                scene.get("id", ""),
                scene.get("name", ""),
                scene.get("type", ""),
                scene.get("description", ""),
                world_id,
            ),
        )

    async def save_object(self, obj: SceneObject) -> None:
        """写入单条场景对象."""
        await self._db.execute(
            "INSERT OR REPLACE INTO scene_objects "
            "(id, name, object_type, scene_id, position_x, position_y, interactable, interact_data, world_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                obj.id,
                obj.name,
                obj.object_type.value,
                obj.scene_id,
                0,
                0,
                int(obj.interactable),
                json.dumps(obj.interact_data, ensure_ascii=False) if obj.interact_data else None,
                obj.world_id,
            ),
        )

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
