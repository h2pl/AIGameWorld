"""场景仓储 / Scene Repository."""

import contextlib
import json

from ..domain import Scene, SceneObject, SceneObjectType
from ..storage.sqlite_client import SQLiteClient
from ..utils.tracing import traced


class SceneRepo:
    """场景对象存取——读全部 + 写单条 + 写场景."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    @traced()
    async def list_scenes(self, world_id: str) -> list[Scene]:
        """按 world_id 加载场景摘要列表."""
        rows = await self._db.fetch_all(
            "SELECT id, name, type, description, spawn_x, spawn_y, map_width, map_height, tilemap_summary, ext_json FROM scenes WHERE world_id = ?",
            (world_id,),
        )
        return [_row_to_scene(r, world_id) for r in rows]

    @traced()
    async def get_scene(self, scene_id: str) -> Scene | None:
        """按 scene_id 加载单个场景."""
        row = await self._db.fetch_one(
            "SELECT id, name, type, description, spawn_x, spawn_y, map_width, map_height, tilemap_summary, ext_json, world_id FROM scenes WHERE id = ?",
            (scene_id,),
        )
        if not row:
            return None
        return _row_to_scene(row)

    @traced()
    async def save_scene(self, scene: Scene, world_id: str) -> None:
        """写入单条场景."""
        await self._db.execute(
            "INSERT OR REPLACE INTO scenes "
            "(id, name, type, description, spawn_x, spawn_y, map_width, map_height, tilemap_summary, ext_json, world_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))",
            (
                scene.id,
                scene.name,
                scene.type,
                scene.description,
                scene.spawn_x,
                scene.spawn_y,
                scene.map_width,
                scene.map_height,
                scene.tilemap_summary,
                scene.ext_json,
                world_id or scene.world_id,
            ),
        )
        await self._db.commit()

    @traced()
    async def save_tilemap_summary(self, scene_id: str, summary: str) -> None:
        """更新场景 tilemap 语义摘要 / Update tilemap semantic summary."""
        await self._db.execute(
            "UPDATE scenes SET tilemap_summary = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (summary, scene_id),
        )
        await self._db.commit()

    @traced()
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

    @traced()
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

    @traced()
    async def get_object_ids(self, scene_id: str) -> list[str]:
        """按 scene_id 查询场景物体 id 列表 / List scene object ids by scene."""
        rows = await self._db.fetch_all(
            "SELECT id FROM scene_objects WHERE scene_id = ?",
            (scene_id,),
        )
        return [r["id"] for r in rows]

    @traced()
    async def delete_by_world(self, world_id: str) -> None:
        """删除指定 world 下所有场景及场景对象 / Delete all scenes and objects for a world."""
        await self._db.execute("DELETE FROM scene_objects WHERE world_id = ?", (world_id,))
        await self._db.execute("DELETE FROM scenes WHERE world_id = ?", (world_id,))
        await self._db.commit()

    @traced()
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


def _row_to_scene(row, world_id: str = "") -> Scene:
    """数据库行转 Scene 领域模型."""
    ext_json = row.get("ext_json", "{}") or "{}"
    with contextlib.suppress(json.JSONDecodeError):
        json.loads(ext_json)
    return Scene(
        id=row["id"],
        name=row.get("name", ""),
        type=row.get("type", ""),
        description=row.get("description", ""),
        spawn_x=row.get("spawn_x", 0),
        spawn_y=row.get("spawn_y", 0),
        map_width=row.get("map_width", 40),
        map_height=row.get("map_height", 40),
        tilemap_summary=row.get("tilemap_summary", ""),
        ext_json=ext_json,
        world_id=world_id or row.get("world_id", ""),
    )
