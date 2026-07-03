"""World CRUD——worlds 表读写 / World repository: create, list."""
# get(id) 用于引擎加载世界观注入 system prompt

from ..domain.world import World
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class WorldRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def create(self, w: World) -> None:
        await self._db.execute(
            "INSERT INTO worlds (id, name, description, version, rule_set, author, starting_scene) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (w.id, w.name, w.description, w.version, w.rule_set, w.author, w.starting_scene),
        )
        await self._db.commit()
        logger.info("[repo] create id=%s name=%s", w.id, w.name)

    async def get(self, world_id: str) -> World | None:
        """按 id 获取单个 world."""
        row = await self._db.fetch_one(
            "SELECT id, name, description, version, rule_set, author, starting_scene FROM worlds WHERE id = ?",
            (world_id,),
        )
        if not row:
            return None
        return World(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            version=row.get("version", "1.0.0"),
            rule_set=row.get("rule_set", "dnd_5e_srd"),
            author=row.get("author", ""),
            starting_scene=row.get("starting_scene", ""),
        )

    async def list_all(self) -> list[World]:
        rows = await self._db.fetch_all(
            "SELECT id, name, description, version, rule_set, author, starting_scene FROM worlds"
        )
        return [
            World(
                id=r["id"],
                name=r["name"],
                description=r.get("description", ""),
                version=r.get("version", "1.0.0"),
                rule_set=r.get("rule_set", "dnd_5e_srd"),
                author=r.get("author", ""),
                starting_scene=r.get("starting_scene", ""),
            )
            for r in rows
        ]
