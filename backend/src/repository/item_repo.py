"""物品仓储."""

import json

from ..domain import Item, ItemType
from ..storage.sqlite_client import SQLiteClient


class ItemRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def load_all(self) -> dict[str, Item]:
        rows = await self._db.fetch_all("SELECT * FROM items")
        return {
            r["id"]: Item(
                id=r["id"],
                name=r["name"],
                item_type=ItemType(r["item_type"]),
                rarity=r.get("rarity", "common"),
                weight=r.get("weight", 0.0),
                value=r.get("value", 0),
                description=r.get("description", ""),
                data=json.loads(r.get("data_json", "{}")),
                pack_name=r["pack_name"],
            )
            for r in rows
        }
