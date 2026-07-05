"""DM 记录仓储 / DM Records Repository."""

import json

from ..domain.dm_record import DMRecord
from ..domain.story_summary import StorySummary
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DMRecordRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    # ── DM Records ──

    async def save_plot_brief(self, record: DMRecord) -> None:
        """写入 plot_brief + hints + ext（dm_create 阶段）."""
        logger.info("[repo] save_plot_brief tick=%s", record.tick)
        await self._db.execute(
            """INSERT INTO dm_records (world_id, tick, plot_brief, hint_list, dm_narrative, ext_json)
               VALUES (?, ?, ?, ?, '', ?)
               ON CONFLICT(world_id, tick) DO UPDATE SET
               plot_brief = excluded.plot_brief, hint_list = excluded.hint_list, ext_json = excluded.ext_json""",
            (
                record.world_id,
                record.tick,
                record.plot_brief,
                json.dumps(record.hints),
                json.dumps(record.ext),
            ),
        )
        await self._db.commit()

    async def update_narrative(self, record: DMRecord) -> None:
        """更新 dm_narrative + ext（dm_narrate 阶段）."""
        logger.info("[repo] update_narrative tick=%s", record.tick)
        await self._db.execute(
            """UPDATE dm_records SET dm_narrative = ?, ext_json = ?, updated_at = datetime('now', '+08:00')
               WHERE world_id = ? AND tick = ?""",
            (record.dm_narrative, json.dumps(record.ext), record.world_id, record.tick),
        )
        await self._db.commit()

    async def max_tick(self, world_id: str) -> int:
        """获取 world 下最大 tick 号."""
        row = await self._db.fetch_one(
            "SELECT MAX(tick) as m FROM dm_records WHERE world_id = ?", (world_id,)
        )
        return row["m"] if row and row["m"] is not None else 0

    async def load_latest_plot_brief(self, world_id: str, before_tick: int) -> str:
        """加载 before_tick 之前最新的 plot_brief."""
        row = await self._db.fetch_one(
            "SELECT plot_brief FROM dm_records WHERE world_id = ? AND tick < ? AND plot_brief != '' "
            "ORDER BY tick DESC LIMIT 1",
            (world_id, before_tick),
        )
        return row["plot_brief"] if row and row["plot_brief"] else ""

    async def load_by_world(self, world_id: str, limit: int = 50) -> list[DMRecord]:
        """按 world 加载 DM 记录（按 tick 升序）."""
        rows = await self._db.fetch_all(
            "SELECT world_id, tick, plot_brief, hint_list, dm_narrative, ext_json FROM dm_records "
            "WHERE world_id = ? ORDER BY tick DESC LIMIT ?",
            (world_id, limit),
        )
        return [_row_to_record(r) for r in reversed(rows)]

    async def load_range(self, world_id: str, tick_start: int, tick_end: int) -> list[DMRecord]:
        """按 tick 范围加载 DM 记录."""
        rows = await self._db.fetch_all(
            "SELECT world_id, tick, plot_brief, hint_list, dm_narrative, ext_json FROM dm_records "
            "WHERE world_id = ? AND tick BETWEEN ? AND ? ORDER BY tick",
            (world_id, tick_start, tick_end),
        )
        return [_row_to_record(r) for r in rows]

    # ── Story Summaries ──

    async def insert_summary(self, summary: StorySummary) -> None:
        """插入一条故事摘要."""
        logger.info("[repo] insert_summary ticks=%s-%s", summary.tick_start, summary.tick_end)
        await self._db.execute(
            """INSERT OR REPLACE INTO story_summaries (world_id, tick_start, tick_end, summary)
               VALUES (?, ?, ?, ?)""",
            (summary.world_id, summary.tick_start, summary.tick_end, summary.summary),
        )
        await self._db.commit()

    async def delete_by_world(self, world_id: str) -> None:
        """删除指定 world 下所有 DM 记录 / Delete all DM records for a world."""
        await self._db.execute("DELETE FROM dm_records WHERE world_id = ?", (world_id,))
        await self._db.commit()

    async def delete_summaries_by_world(self, world_id: str) -> None:
        """删除指定 world 下所有摘要 / Delete all summaries for a world."""
        await self._db.execute("DELETE FROM story_summaries WHERE world_id = ?", (world_id,))
        await self._db.commit()

    async def load_summaries(self, world_id: str) -> list[StorySummary]:
        """按 world 加载所有摘要."""
        rows = await self._db.fetch_all(
            "SELECT world_id, tick_start, tick_end, summary FROM story_summaries "
            "WHERE world_id = ? ORDER BY tick_start",
            (world_id,),
        )
        return [
            StorySummary(
                world_id=r["world_id"],
                tick_start=r["tick_start"],
                tick_end=r["tick_end"],
                summary=r["summary"],
            )
            for r in rows
        ]


def _row_to_record(r: dict) -> DMRecord:
    return DMRecord(
        world_id=r["world_id"],
        tick=r["tick"],
        plot_brief=r["plot_brief"],
        hints=json.loads(r.get("hint_list", "[]")),
        dm_narrative=r["dm_narrative"],
        ext=json.loads(r.get("ext_json", "{}")),
    )
