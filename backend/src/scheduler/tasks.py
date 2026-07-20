"""调度任务 / Scheduler Tasks.

- Reflector: 异步轮询 PC 短期记忆，触发反思引擎，写入长期/关系记忆
"""

import asyncio

from ..repository.memory_repo import MemoryRepo
from ..repository.pc_repo import PcRepo
from ..utils.logging import get_logger
from ..engine.reflection import reflection_engine

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
            # 取出最近的短期记忆 (从内存 deque)
            recent_mems = list(self._memory_repo._short_queue(pc.id))
            if not recent_mems:
                continue

            current_tick = recent_mems[-1].tick

            # 触发条件 1: 定期反思 (比如每 50 个 tick)
            time_to_reflect = (current_tick > 0 and current_tick % 50 == 0)

            # 触发条件 2: 突发极高重要性事件 (>= 8)
            big_event = recent_mems[-1].importance >= 8

            # 触发条件 3: 累计重要度超过阈值
            cumulative = False
            past_refs = await self._memory_repo.retrieve_reflections(pc.id, query="", top_k=1)
            last_reflect_tick = past_refs[0].tick if past_refs else 0

            if self._memory_repo._sqlite:
                rows = await self._memory_repo._sqlite.fetch_all(
                    "SELECT SUM(importance) as total FROM memories WHERE pc_id = ? AND tick > ? AND memory_type != 'reflection'",
                    (pc.id, last_reflect_tick)
                )
                total_importance = rows[0]["total"] if rows and rows[0]["total"] else 0
                if total_importance >= self._threshold:
                    cumulative = True

            if time_to_reflect or big_event or cumulative:
                logger.info(f"[scheduler] Triggering reflection for PC {pc.name} (tick={current_tick})")

                # 获取历史反思上下文
                past_refs_full = await self._memory_repo.retrieve_reflections(pc.id, "behavior growth", top_k=3)
                past_texts = [r.content for r in past_refs_full]

                # 调用底层 Reflection Engine (LLM)
                results = await reflection_engine.reflect(
                    pc_id=pc.id,
                    pc_name=pc.name,
                    pc_type="pc",
                    arc_stage=pc.character_arc.stage if pc.character_arc else "",
                    arc_description=pc.character_arc.description if pc.character_arc else "",
                    memories=recent_mems[-10:],  # 把最近的记忆发给 LLM
                    recent_reflections=past_texts,
                    tick=current_tick,
                    config={"configurable": {"llm": self._llm}} if self._llm else None,
                )

                if results:
                    insight = results[0]["insight"]
                    # 写入长期记忆 ChromaDB + SQLite
                    await self._memory_repo.store_reflection(pc.id, insight, current_tick, self._world_id)
                    logger.info(f"[scheduler] Reflection completed for {pc.name}: {insight[:30]}...")
