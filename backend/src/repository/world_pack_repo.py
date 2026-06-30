"""世界包仓储 / World Pack Repository."""

from ..domain.world_pack import WorldPack
from ..storage.sqlite_client import SQLiteClient


class WorldPackRepo:
    """世界包存取 / Save & load world-pack metadata."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    async def save(self, pack: WorldPack) -> None:
        """写入或更新 world_pack 记录 / Insert or update world_pack record."""
        await self._db.execute(
            "INSERT OR REPLACE INTO world_pack "
            "(id, name, description, version, rule_set, author, license, theme, starting_scene) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pack.id,
                pack.name,
                pack.description,
                pack.version,
                pack.rule_set,
                pack.author,
                pack.license,
                pack.theme,
                pack.starting_scene,
            ),
        )

    async def load(self, pack_id: str) -> WorldPack | None:
        """按 ID 加载单个 pack / Load a single pack by ID."""
        row = await self._db.fetch_one(
            "SELECT id, name, description, version, rule_set, author, license, theme, starting_scene "
            "FROM world_pack WHERE id = ?",
            (pack_id,),
        )
        if row is None:
            return None
        return WorldPack(**dict(row))

    async def load_all(self) -> list[WorldPack]:
        """加载所有 pack / Load all packs."""
        rows = await self._db.fetch_all(
            "SELECT id, name, description, version, rule_set, author, license, theme, starting_scene "
            "FROM world_pack ORDER BY id"
        )
        return [WorldPack(**dict(r)) for r in rows]
