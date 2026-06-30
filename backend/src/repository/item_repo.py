"""物品仓储 / Item Repository."""

import json

from ..domain import Item, ItemType
from ..storage.sqlite_client import SQLiteClient


class ItemRepo:
    """物品存取——读全部 + 写单条."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    async def save(self, item: Item) -> None:
        """写入单条物品 / Save single item."""
        await self._db.execute(
            "INSERT OR REPLACE INTO items "
            "(id, name, item_type, rarity, weight, value, description, data_json, pack_id, pack_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item.id,
                item.name,
                item.item_type.value,
                item.rarity,
                item.weight,
                item.value,
                item.description,
                json.dumps(item.data, ensure_ascii=False),
                item.pack_id,
                item.pack_name,
            ),
        )

    async def load_all(self) -> dict[str, Item]:
        """加载全部物品 / Load all items."""
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
                pack_id=r["pack_id"],
                pack_name=r.get("pack_name", ""),
            )
            for r in rows
        }
