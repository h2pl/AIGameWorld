"""World CRUD + tick 管理."""

from ..domain.world import World
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import get_logger
from ..utils.tracing import traced

logger = get_logger(__name__)


class WorldRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    @traced()
    async def create(self, w: World) -> None:
        await self._db.execute(
            "INSERT INTO worlds (id, name, description, version, rule_set, author, "
            "starting_scene_id, current_scene_id, status, data_tick, display_tick, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))",
            (
                w.id,
                w.name,
                w.description,
                w.version,
                w.rule_set,
                w.author,
                w.starting_scene_id,
                w.current_scene_id,
                w.status,
                w.data_tick,
                w.display_tick,
            ),
        )
        await self._db.commit()
        logger.info("[repo] create id=%s status=%s", w.id, w.status)

    @traced()
    async def get(self, world_id: str) -> World | None:
        row = await self._db.fetch_one(
            "SELECT id, name, description, version, rule_set, author, "
            "starting_scene_id, current_scene_id, status, data_tick, display_tick "
            "FROM worlds WHERE id = ?",
            (world_id,),
        )
        return _row_to_world(row) if row else None

    @traced()
    async def list_all(self) -> list[World]:
        rows = await self._db.fetch_all(
            "SELECT id, name, description, version, rule_set, author, "
            "starting_scene_id, current_scene_id, status, data_tick, display_tick FROM worlds"
        )
        return [_row_to_world(r) for r in rows]

    @traced()
    async def get_status(self, world_id: str) -> str:
        """读取世界初始化状态，world 不存在返回空串 / Read world init status."""
        row = await self._db.fetch_one("SELECT status FROM worlds WHERE id = ?", (world_id,))
        return row["status"] if row else ""

    @traced()
    async def set_status(self, world_id: str, status: str) -> None:
        """写入世界初始化状态 / Set world init status (init -> ready)."""
        await self._db.execute(
            "UPDATE worlds SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (status, world_id),
        )
        await self._db.commit()

    @traced()
    async def set_current_scene_id(self, world_id: str, scene_id: str) -> None:
        """持久化世界当前主场景（party 裁决 / world_init 写入）/
        Persist world's current main scene."""
        await self._db.execute(
            "UPDATE worlds SET current_scene_id = ?, updated_at = datetime('now', 'localtime') "
            "WHERE id = ?",
            (scene_id, world_id),
        )
        await self._db.commit()

    @traced()
    async def get_data_tick(self, world_id: str) -> int:
        """获取后端已生成的最新 data_tick，world 不存在返回 0."""
        row = await self._db.fetch_one(
            "SELECT data_tick FROM worlds WHERE id = ?",
            (world_id,),
        )
        return row["data_tick"] if row else 0

    @traced()
    async def get_display_tick(self, world_id: str) -> int:
        """获取前端已展示到的 tick，world 不存在返回 0."""
        row = await self._db.fetch_one(
            "SELECT display_tick FROM worlds WHERE id = ?",
            (world_id,),
        )
        return row["display_tick"] if row else 0

    @traced()
    async def increment_data_tick(self, world_id: str) -> int:
        """data_tick +1 并返回新值."""
        await self._db.execute(
            "UPDATE worlds SET data_tick = data_tick + 1, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (world_id,),
        )
        await self._db.commit()
        row = await self._db.fetch_one(
            "SELECT data_tick FROM worlds WHERE id = ?",
            (world_id,),
        )
        return row["data_tick"] if row else 0

    @traced()
    async def set_data_tick(self, world_id: str, tick: int) -> None:
        """时光倒流专用：直接设置 data_tick / Set data_tick directly for time travel."""
        await self._db.execute(
            "UPDATE worlds SET data_tick = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (tick, world_id),
        )
        await self._db.commit()

    @traced()
    async def set_display_tick(self, world_id: str, tick: int) -> None:
        """更新前端已展示到的 tick."""
        await self._db.execute(
            "UPDATE worlds SET display_tick = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (tick, world_id),
        )
        await self._db.commit()

    @traced()
    async def reset_tick(self, world_id: str) -> None:
        """重置 data_tick 和 display_tick 为 0，状态置回 init 并清空当前场景（下次 tick 重新初始化）/
        Reset ticks, revert status to init, clear current_scene so next tick re-runs world_init."""
        await self._db.execute(
            "UPDATE worlds SET data_tick = 0, display_tick = 0, status = 'init', "
            "current_scene_id = '', updated_at = datetime('now', 'localtime') WHERE id = ?",
            (world_id,),
        )
        await self._db.commit()

    @traced()
    async def delete(self, world_id: str) -> None:
        """删除指定 world 记录 / Delete a world record."""
        await self._db.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
        await self._db.commit()
        logger.info("[repo] delete id=%s", world_id)


def _row_to_world(row: dict) -> World:
    return World(
        id=row["id"],
        name=row["name"],
        description=row.get("description", ""),
        version=row.get("version", "1.0.0"),
        rule_set=row.get("rule_set", "dnd_5e_srd"),
        author=row.get("author", ""),
        starting_scene_id=row.get("starting_scene_id", ""),
        current_scene_id=row.get("current_scene_id", ""),
        status=row.get("status", "ready"),
        data_tick=row.get("data_tick", 0),
        display_tick=row.get("display_tick", 0),
    )
