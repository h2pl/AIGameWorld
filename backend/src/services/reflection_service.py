"""Reflection Service——遍历角色 + 重要性阈值检查 + 调用 Engine + 归零.

遍历所有角色，对 PC（阈值 100）和 Actor（阈值 200）分别调用反思 Engine。
反思后 importance_accumulator 归零，insight 存入 MemoryRepo。
"""

from langchain_core.runnables.config import RunnableConfig

from ..engine.reflection import reflection_engine
from ..graph.state import ReflectionSubState
from ..schemas.request import ReflectionRequest
from ..utils.helpers import get_repo
from ..utils.logging import get_logger

logger = get_logger(__name__)

_PC_THRESHOLD = 100
_ACTOR_THRESHOLD = 200


async def reflect(state: ReflectionSubState, config: RunnableConfig = None) -> dict:
    """Phase 7: 遍历所有角色执行反思 / Reflect on all characters."""
    pc_repo = get_repo(config, "char")
    memory_repo = get_repo(config, "memory")
    if not pc_repo or not memory_repo:
        return {"reflected_pcs": []}

    insights = []
    tick = state.get("tick", 0)

    # PC 反思 / PC reflection
    for pc in await pc_repo.load_pcs():
        if _needs_reflection(memory_repo, pc.id, _PC_THRESHOLD):
            insight = await _reflect_one(
                reflection_engine,
                pc.id,
                pc.name,
                "pc",
                pc.character_arc.stage if pc.character_arc else "",
                pc.character_arc.description if pc.character_arc else "",
                memory_repo,
                tick,
                config,
            )
            if insight:
                insights.append(insight)
                memory_repo.store_reflection(pc.id, insight["insight"], tick)
                pc.importance_accumulator = 0.0
                await pc_repo.save_pc(pc)

    # Actor 反思 / Actor reflection
    for actor in await pc_repo.load_actors():
        if _needs_reflection(memory_repo, actor.id, _ACTOR_THRESHOLD):
            insight = await _reflect_one(
                reflection_engine,
                actor.id,
                actor.name,
                "actor",
                actor.character_arc.stage if actor.character_arc else "",
                actor.character_arc.description if actor.character_arc else "",
                memory_repo,
                tick,
                config,
            )
            if insight:
                insights.append(insight)
                memory_repo.store_reflection(actor.id, insight["insight"], tick)
                actor.importance_accumulator = 0.0
                await pc_repo.save_actor(actor)

    return {"reflected_pcs": [i["pc_id"] for i in insights]}


def _needs_reflection(memory_repo, pc_id: str, threshold: int) -> bool:
    """判断是否触发反思 / Check if reflection should trigger."""
    recent = list(memory_repo._short_queue(pc_id))
    return sum(m.importance for m in recent) >= threshold


async def _reflect_one(
    engine,
    char_id: str,
    name: str,
    char_type: str,
    arc_stage: str,
    arc_desc: str,
    memory_repo,
    tick: int,
    config,
) -> dict | None:
    """对单个角色执行反思 / Reflect on a single character."""
    recent_mems = list(memory_repo._short_queue(char_id))[-5:]
    past_refs = memory_repo.retrieve_reflections(char_id, "behavior growth", top_k=3)
    past_texts = [r.content for r in past_refs]

    result = await engine.reflect(
        ReflectionRequest(
            pc_id=char_id,
            pc_name=name,
            pc_type=char_type,
            arc_stage=arc_stage,
            arc_description=arc_desc,
            memories=[{"content": m.content, "importance": m.importance} for m in recent_mems],
            recent_reflections=past_texts,
            tick=tick,
        ),
        config,
    )

    if result.insights_out:
        return result.insights_out[0]
    return None
