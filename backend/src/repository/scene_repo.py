"""场景仓储 / Scene Repository."""

import json

from ..domain import SceneObject, SceneObjectType
from ..storage.sqlite_client import SQLiteClient


class SceneRepo:
    """场景对象存取——读全部 + 写单条 + 写场景."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    async def save_scene(self, scene: dict, world_id: str, world_name: str) -> None:
        """写入单条场景 / Save single scene_engine."""
        await self._db.execute(
            "INSERT OR REPLACE INTO scenes "
            "(id, name, type, description, exits_json, landmarks_json, world_id, world_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scene_engine.get("id", ""),
                scene_engine.get("name", ""),
                scene_engine.get("type", ""),
                scene_engine.get("description", ""),
                json.dumps(scene_engine.get("exits", []), ensure_ascii=False),
                json.dumps(scene_engine.get("landmarks", []), ensure_ascii=False),
                world_id,
                world_name,
            ),
        )

    async def save_object(self, obj: SceneObject) -> None:
        """写入单条场景对象 / Save single scene object."""
        await self._db.execute(
            "INSERT OR REPLACE INTO scene_objects "
            "(id, name, object_type, scene_id, position_x, position_y, interactable, interact_data_json, world_id) "
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
        """加载全部场景对象 / Load all scene objects."""
        rows = await self._db.fetch_all("SELECT * FROM scene_objects")
        result = {}
        for r in rows:
            idata = r.get("interact_data_json")
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
