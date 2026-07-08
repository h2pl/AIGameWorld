"""Memory Service——为各引擎提供按需记忆注入 / Memory injection service for engines.

统一封装短期/中期/长期记忆的检索，供 prompt 注入。
重要性评分 = 事件类型 base 分 + 时间衰减 + 近期加成，不引入额外 LLM。
"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import Memory
from ..repository.memory_repo import score_memory
from ..utils.helpers import get_repo, is_mock


async def retrieve_memories(
    pc_id: str,
    query: str,
    config: RunnableConfig = None,
    top_k: int = 5,
    memory_types: list[str] | None = None,
    periods: list[str] | None = None,
    include_reflections: bool = True,
    memories: dict[str, list[Memory]] | None = None,
    current_tick: int = 0,
) -> list[str]:
    """按角色 + 查询语义检索相关记忆文本 / Retrieve relevant memory texts for a character.

    返回按综合重要性分数（事件+时间）排序的记忆内容列表；无记忆或 repo 不可用时返回空列表。
    同时包含观察记忆与反思记忆，用于指导角色下一步行动。
    支持按 memory_type 和 period 过滤；支持注入本 tick 尚未落盘的新记忆。
    不过滤记忆类型，按事件和重要性提取。

    Mock 模式下跳过 Chroma 长期语义检索，避免本地 embedding 模型加载导致 E2E 超时。
    """
    # Mock 模式：只使用本 tick 已产生的记忆，避免 Chroma embedding 查询耗时
    if is_mock(config):
        contents: list[str] = []
        seen: set[str] = set()
        if memories:
            current_mems = memories.get(pc_id, [])
            scored = sorted(
                current_mems,
                key=lambda m: score_memory(m.importance, m.tick, current_tick),
                reverse=True,
            )
            for m in scored[:top_k]:
                content = m.content
                if content and content not in seen:
                    contents.append(content)
                    seen.add(content)
        return contents

    memory_repo = get_repo(config, "memory")
    if not memory_repo:
        return []
    try:
        observations = await memory_repo.retrieve(
            pc_id,
            query,
            top_k=top_k,
            memory_types=memory_types,
            periods=periods,
            entity_types=["pc", "actor"],
            current_tick=current_tick,
        )
        contents: list[str] = []
        seen: set[str] = set()

        # 1) 本 tick 已产生但尚未落盘的新记忆（score 排序）
        if memories:
            current_mems = memories.get(pc_id, [])
            scored = sorted(
                current_mems,
                key=lambda m: score_memory(m.importance, m.tick, current_tick),
                reverse=True,
            )
            for m in scored[:top_k]:
                content = m.content
                if content and content not in seen:
                    contents.append(content)
                    seen.add(content)

        # 2) 反思记忆
        if include_reflections:
            reflections = await memory_repo.retrieve_reflections(
                pc_id, query, top_k=3, current_tick=current_tick
            )
            for m in reflections:
                content = getattr(m, "content", None)
                if content and content not in seen:
                    contents.append(content)
                    seen.add(content)

        # 3) 观察/行为记忆
        for m in observations:
            content = getattr(m, "content", None)
            if content and content not in seen:
                contents.append(content)
                seen.add(content)
        return contents
    except TypeError:
        return []


async def retrieve_dm_records(
    world_id: str,
    config: RunnableConfig = None,
    top_k: int = 5,
    before_tick: int | None = None,
) -> list[str]:
    """检索 DM 记录作为 DM 记忆 / Retrieve DM records as DM memory texts.

    复用 dm_records 表，不需要单独的 dm_memories 表。
    返回最近 ticks 的 plot_brief + dm_narrative 拼接文本。
    """
    dm_record_repo = get_repo(config, "dm_record")
    if not dm_record_repo:
        return []
    try:
        records = await dm_record_repo.load_by_world(world_id, limit=top_k)
        contents: list[str] = []
        for r in records:
            if before_tick is not None and r.tick >= before_tick:
                continue
            parts: list[str] = []
            if r.plot_brief:
                parts.append(f"[tick {r.tick}] 剧情：{r.plot_brief}")
            if r.dm_narrative:
                parts.append(f"[tick {r.tick}] 叙事：{r.dm_narrative}")
            if parts:
                contents.append("\n".join(parts))
        return contents
    except TypeError:
        return []
