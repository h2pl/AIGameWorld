"""Reflection Service——遍历 PC + 重要性阈值检查 + 调用 Engine + 归零.

仅对 PC 做反思，Actor 不做反思也不记记忆。
"""

from langchain_core.runnables.config import RunnableConfig

from ..engine.reflection import reflection_engine
from ..graph.state import ReflectionSubState
from ..utils.helpers import get_repo, is_mock
from ..utils.logging import get_logger

logger = get_logger(__name__)

_PC_THRESHOLD = 100


async def reflect(state: ReflectionSubState, config: RunnableConfig = None) -> dict:
    """Phase 7: 遍历所有 PC 执行反思 / Reflect on all PCs."""
    # Mock 模式下跳过反思，避免 Chroma 检索/写入拖慢 E2E
    if is_mock(config):
        return {"reflected_pcs": []}

    pc_repo = get_repo(config, "char")
    memory_repo = get_repo(config, "memory")
    if not pc_repo or not memory_repo:
        return {"reflected_pcs": []}

    insights = []
    tick = state.get("tick", 0)
    world_id = state.get("world_id")

    for pc in await pc_repo.load_all(world_id):
        if await _needs_reflection(memory_repo, pc.id, _PC_THRESHOLD, tick):
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
                await memory_repo.store_reflection(pc.id, insight["insight"], tick, world_id or "")
                pc.importance_accumulator = 0.0
                await pc_repo.save(pc)

    return {"reflected_pcs": [i["pc_id"] for i in insights]}


async def _needs_reflection(memory_repo, pc_id: str, threshold: int, tick: int) -> bool:
    """判断是否触发反思 (基于斯坦福小镇成熟架构) / Check if reflection should trigger.
    1. 定期反思：每 50 个 tick 定期触发一次 (类似每天晚上反思)
    2. 突发重大事件：短期记忆中出现了 importance >= 8 的极重要事件
    3. 累计阈值：自上次反思以来的记忆重要度累计超过阈值 (默认 100)
    """
    # 1. 周期性触发 (定期整理记忆)
    if tick > 0 and tick % 50 == 0:
        return True

    recent_mems = list(memory_repo._short_queue(pc_id))
    if not recent_mems:
        return False

    # 2. 突发重大事件触发 (例如：被攻击、目击死亡)
    if recent_mems[-1].importance >= 8:
        return True

    # 3. 累计重要度触发
    # 查找上一次反思的 tick
    past_refs = await memory_repo.retrieve_reflections(pc_id, query="", top_k=1)
    last_reflect_tick = past_refs[0].tick if past_refs else 0

    # 统计自上次反思以来的重要度总和 (通过 SQLite 快速聚合)
    if memory_repo._sqlite:
        rows = await memory_repo._sqlite.fetch_all(
            "SELECT SUM(importance) as total FROM memories WHERE pc_id = ? AND tick > ? AND memory_type != 'reflection'",
            (pc_id, last_reflect_tick)
        )
        total_importance = rows[0]["total"] if rows and rows[0]["total"] else 0
        if total_importance >= threshold:
            return True

    return False


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
    past_refs = await memory_repo.retrieve_reflections(char_id, "behavior growth", top_k=3)
    past_texts = [r.content for r in past_refs]

    results = await engine.reflect(
        pc_id=char_id,
        pc_name=name,
        pc_type=char_type,
        arc_stage=arc_stage,
        arc_description=arc_desc,
        memories=recent_mems,
        recent_reflections=past_texts,
        tick=tick,
        config=config,
    )

    if results:
        return results[0]
    return None
