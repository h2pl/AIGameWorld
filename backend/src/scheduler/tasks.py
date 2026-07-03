"""调度任务 / Scheduler Tasks.

# RecordArchiver 轮询 dm_records → ChromaDB, Summarizer 每10tick 摘要双写
独立于主 tick 链路，纯异步轮询：
# Summarizer._generate 调用 LLM 摘要，降级时截断到200字
# 每2s轮询一次，从ChromaDB恢复断点
- RecordArchiver: dm_records + tick_events → ChromaDB
# 每2s轮询，从ChromaDB恢复断点继续归档
- Summarizer: 每 N tick 摘要 → story_summaries + ChromaDB 双写
"""

import asyncio

from ..domain.dm_record import DMRecord
from ..domain.story_summary import StorySummary
from ..repository.dm_record_repo import DMRecordRepo
from ..storage.chroma_client import ChromaClient
from ..utils.logging import get_logger

logger = get_logger(__name__)

_SUMMARY_INTERVAL = 10


class RecordArchiver:
    """任务 1：轮询 dm_records + tick_events，归档到 ChromaDB."""

    def __init__(self, world_id: str, record_repo: DMRecordRepo, event_repo, chroma: ChromaClient):
        self._world_id = world_id
        self._repo = record_repo
        self._event_repo = event_repo
        self._chroma = chroma
        self._collection = f"dm_memory_{world_id}"
        self._last = 0

    async def run(self, interval: float = 2.0) -> None:
        logger.info("[scheduler] started world=%s", self._world_id)
        self._last = self._restore_last()
        while True:
            try:
                await self._poll()
            except Exception:
                logger.exception("[scheduler] poll error")
            await asyncio.sleep(interval)

    async def _poll(self) -> None:
        max_tick = await self._repo.max_tick(self._world_id)
        if max_tick <= self._last:
            return
        start = self._last + 1
        records = await self._repo.load_range(self._world_id, start, max_tick)
        if not records:
            return
        tick_events = (
            await self._event_repo.load_by_tick_range(self._world_id, start, max_tick)
            if self._event_repo
            else []
        )
        tick_events_by_tick: dict[int, list[str]] = {}
        for ev in tick_events:
            tick_events_by_tick.setdefault(ev["tick"], []).append(f"[{ev['type']}] {ev['payload']}")

        ids = [f"{self._world_id}_{r.tick}" for r in records]
        docs = [_build_document(r, tick_events_by_tick.get(r.tick, [])) for r in records]
        metas = [{"world_id": self._world_id, "tick": r.tick, "type": "record"} for r in records]
        self._chroma.add(self._collection, ids=ids, documents=docs, metadatas=metas)
        self._last = max_tick
        logger.info("[scheduler] archived %d-%d (%d records)", start, max_tick, len(records))

    def _restore_last(self) -> int:
        try:
            col = self._chroma.get_collection(self._collection)
            if col.count() == 0:
                return 0
            res = col.get(where={"type": "record"}, include=["metadatas"])
            if res and res["metadatas"]:
                return max(m.get("tick", 0) for m in res["metadatas"])
        except Exception:
            logger.warning("[scheduler] restore failed, starting from 0")
        return 0


class Summarizer:
    """任务 2：轮询 dm_records + tick_events，每 N tick 生成摘要双写 SQLite + ChromaDB."""

    def __init__(
        self, world_id: str, record_repo: DMRecordRepo, event_repo, chroma: ChromaClient, llm=None
    ):
        self._world_id = world_id
        self._repo = record_repo
        self._event_repo = event_repo
        self._chroma = chroma
        self._llm = llm
        self._collection = f"dm_memory_{world_id}"
        self._last_summarized = 0

    async def run(self, interval: float = 3.0) -> None:
        logger.info("[scheduler] started world=%s", self._world_id)
        while True:
            try:
                await self._poll()
            except Exception:
                logger.exception("[scheduler] poll error")
            await asyncio.sleep(interval)

    async def _poll(self) -> None:
        max_tick = await self._repo.max_tick(self._world_id)
        if max_tick - self._last_summarized < _SUMMARY_INTERVAL:
            return
        tick_start = self._last_summarized + 1
        tick_end = max_tick
        summary = await self._generate(tick_start, tick_end)
        if not summary:
            return
        await self._repo.insert_summary(
            StorySummary(
                world_id=self._world_id,
                tick_start=tick_start,
                tick_end=tick_end,
                summary=summary,
            )
        )
        self._chroma.add(
            self._collection,
            ids=[f"{self._world_id}_summary_{tick_start}_{tick_end}"],
            documents=[summary],
            metadatas=[
                {
                    "world_id": self._world_id,
                    "type": "summary",
                    "tick_start": tick_start,
                    "tick_end": tick_end,
                }
            ],
        )
        self._last_summarized = tick_end
        logger.info("[scheduler] summarized %d-%d", tick_start, tick_end)

    async def _generate(self, tick_start: int, tick_end: int) -> str:
        records = await self._repo.load_range(self._world_id, tick_start, tick_end)
        if not records:
            return ""
        tick_events = (
            await self._event_repo.load_by_tick_range(self._world_id, tick_start, tick_end)
            if self._event_repo
            else []
        )
        tick_events_by_tick: dict[int, list[str]] = {}
        for ev in tick_events:
            tick_events_by_tick.setdefault(ev["tick"], []).append(f"[{ev['type']}] {ev['payload']}")

        lines = []
        for r in records:
            lines.append(f"[Tick {r.tick}] {r.plot_brief}\n{r.dm_narrative}")
            if r.tick in tick_events_by_tick:
                lines.append("事件: " + " | ".join(tick_events_by_tick[r.tick]))
        text = "\n".join(lines)

        if self._llm:
            try:
                result = await self._llm.call(
                    "summarize_tick_range",
                    [
                        {
                            "role": "system",
                            "content": "你是剧情摘要员。根据多段叙事和事件列表，浓缩为2-3句连贯摘要，保留关键角色行动和场景变化。",
                        },
                        {"role": "user", "content": f"请总结以下剧情：\n\n{text}"},
                    ],
                )
                return result.strip() if result else text[:200]
            except Exception:
                logger.exception("[scheduler] llm failed, using truncation")
        return text[:200]


def _build_document(r: DMRecord, tick_events: list[str] | None = None) -> str:
    parts = [f"[场景] {r.plot_brief}", f"[叙事] {r.dm_narrative}"]
    if tick_events:
        parts.append("[事件]\n" + "\n".join(tick_events))
    return "\n".join(parts)
