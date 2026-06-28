"""场景仓储."""

import json

from ..domain import SceneObject, SceneObjectType
from ..storage.sqlite_client import SQLiteClient


class SceneRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def load_all(self) -> dict[str, SceneObject]:
        rows = await self._db.fetch_all("SELECT * FROM scene_objects")
        result = {}
        for r in rows:
            idata = r.get("interact_data_json")
            result[r["id"]] = SceneObject(
                id=r["id"], name=r["name"],
                object_type=SceneObjectType(r["object_type"]),
                scene_id=r["scene_id"],
                position_x=r.get("position_x", 0), position_y=r.get("position_y", 0),
                interactable=bool(r.get("interactable", 1)),
                interact_data=json.loads(idata) if idata else None,
            )
        return result
