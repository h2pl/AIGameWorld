"""调度任务 / Scheduler Tasks.

- Reflector: 异步轮询 PC 短期记忆，触发反思引擎，写入长期/关系记忆
- Summarizer: 异步轮询世界 tick，定期压缩 DM 记录为故事摘要
"""

import asyncio

from ..engine.reflection import reflection_engine
from ..repository.dm_record_repo import DMRecordRepo
from ..repository.memory_repo import MemoryRepo
from ..repository.pc_repo import PcRepo
from ..utils.logging import get_logger

logger = get_logger(__name__)


class Reflector:
    """异步轮询 PC 短期记忆，触发反思引擎，写入长期/关系记忆."""

    def __init__(self, world_id: str, memory_repo: MemoryRepo, pc_repo: PcRepo, llm=None):
        self._world_id = world_id
        self._memory_repo = memory_repo
        self._pc_repo = pc_repo
        self._llm = llm
        self._threshold = 100

    async def run(self, interval: float = 5.0) -> None:
        logger.info("[scheduler] Reflector started for world=%s", self._world_id)
        while True:
            try:
                await self._poll()
            except Exception:
                logger.exception("[scheduler] Reflector poll error")
            await asyncio.sleep(interval)

    async def _poll(self) -> None:
        pcs = await self._pc_repo.load_all(self._world_id)
        for pc in pcs:
            # 从 SQLite 读取最近记忆 / Recent memories from SQLite
            recent_mems = await self._memory_repo.get_recent(pc.id, limit=10)
            if not recent_mems:
                continue

            current_tick = recent_mems[0].tick  # DESC 排序，第一条最新

            # 触发条件 1: 定期反思 (比如每 50 个 tick)
            time_to_reflect = current_tick > 0 and current_tick % 50 == 0

            # 触发条件 2: 突发极高重要性事件 (>= 8)
            big_event = recent_mems[0].importance >= 8

            # 触发条件 3: 累计重要度超过阈值
            last_reflect_tick = await self._memory_repo.get_last_reflection_tick(pc.id)
            cumulative = await self._memory_repo.importance_should_reflect(
                pc.id, threshold=self._threshold, since_tick=last_reflect_tick
            )

            if time_to_reflect or big_event or cumulative:
                logger.info(
                    f"[scheduler] Triggering reflection for PC {pc.name} (tick={current_tick})"
                )

                # 获取历史反思上下文（用近期记忆内容构造叙事性 query，匹配反思的语义空间）
                # / Get past reflection context using recent memory content as narrative query
                recent_summary = " ".join(m.content for m in recent_mems[:3])
                context_query = (
                    f"{pc.name} {recent_summary}"
                    if recent_summary
                    else f"{pc.name}的近期经历与成长"
                )
                past_refs_full = await self._memory_repo.retrieve_reflections(
                    pc.id, query=context_query, top_k=3, current_tick=current_tick
                )
                past_texts = [r.content for r in past_refs_full]

                # 解析角色弧 JSON / Parse character arc from arc_json
                import json as _json

                arc_data = _json.loads(pc.arc_json) if pc.arc_json else {}
                arc_stage = arc_data.get("stage", "")
                arc_description = arc_data.get("description", "")

                # 调用底层 Reflection Engine (LLM)
                results = await reflection_engine.reflect(
                    pc_id=pc.id,
                    pc_name=pc.name,
                    pc_type="pc",
                    arc_stage=arc_stage,
                    arc_description=arc_description,
                    memories=recent_mems,  # 把最近的记忆发给 LLM
                    recent_reflections=past_texts,
                    tick=current_tick,
                    config={"configurable": {"llm": self._llm}} if self._llm else None,
                )

                if results:
                    insight = results[0]["insight"]
                    # 写入长期记忆 ChromaDB + SQLite
                    await self._memory_repo.store_reflection(
                        pc.id, insight, current_tick, self._world_id
                    )
                    logger.info(
                        f"[scheduler] Reflection completed for {pc.name}: {insight[:30]}..."
                    )


class Summarizer:
    """异步轮询世界 tick，定期压缩 DM 记录为故事摘要 / Async DM summary consolidation."""

    def __init__(self, world_id: str, dm_record_repo: DMRecordRepo, llm=None):
        self._world_id = world_id
        self._dm_record_repo = dm_record_repo
        self._llm = llm
        self._last_summarized_tick = 0

    async def run(self, interval: float = 10.0) -> None:
        logger.info("[scheduler] Summarizer started for world=%s", self._world_id)
        while True:
            try:
                await self._poll()
            except Exception:
                logger.exception("[scheduler] Summarizer poll error")
            await asyncio.sleep(interval)

    async def _poll(self) -> None:
        from ..services.context_service import generate_dm_summary

        # 获取当前最新 tick / Get latest tick from dm_records
        records = await self._dm_record_repo.load_by_world(self._world_id, limit=1)
        if not records:
            return

        current_tick = records[0].tick
        if current_tick <= self._last_summarized_tick:
            return

        # 委托 context_service 执行摘要生成（内部判断 tick % 10）
        config = (
            {"configurable": {"llm": self._llm, "dm_record": self._dm_record_repo}}
            if self._llm
            else None
        )
        await generate_dm_summary(self._world_id, current_tick, config=config)
        self._last_summarized_tick = current_tick
