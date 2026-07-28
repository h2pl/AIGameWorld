"""Memory Service——为各引擎提供按需记忆注入 / Memory injection service for engines.

三种记忆类型：
1. 短期记忆 (Short-Term)：deque 窗口，最近发生的事
2. 长期记忆 (Long-Term)：ChromaDB 语义检索 + SQLite 补全
3. 反思记忆 (Reflection)：LLM 生成的抽象洞察
"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import Memory
from ..repository.memory_repo import score_memory
from ..utils.helpers import get_repo, is_mock


async def compress_context(query: str, raw_memories: list[str], llm) -> list[str]:
    """如果长上下文过长，调用轻量级模型对记忆进行压缩提炼 / Compress long memory contexts."""
    if not raw_memories or not llm:
        return raw_memories
        
    # 如果记忆条数不多，或者总长度可控，则不压缩以节省延迟
    total_len = sum(len(m) for m in raw_memories)
    if len(raw_memories) <= 3 or total_len < 1000:
        return raw_memories
        
    # 构建压缩 Prompt
    prompt = f"当前情境或意图：{query}\n\n"
    prompt += "以下是从角色记忆库中检索到的相关片段：\n"
    for i, m in enumerate(raw_memories):
        prompt += f"[{i+1}] {m}\n"
    prompt += "\n请根据当前情境，将上述记忆压缩提炼成3-5条最核心的线索。过滤掉不相关的冗余细节。直接输出要点，不要任何寒暄。"
    
    from langchain_core.messages import HumanMessage
    
    try:
        compressed_text = await llm.call(
            purpose="reflection",  # 复用 reflection 的 LLM 配置，通常较轻量
            tick_messages=[HumanMessage(content=prompt)]
        )
        if compressed_text:
            return [line.strip("- ") for line in compressed_text.split("\n") if line.strip()]
    except Exception as e:
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"[memory_service] Context compression failed: {e}")
        
    # 失败则降级返回原数据
    return raw_memories

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
    """检索角色相关记忆，按综合分数排序返回内容文本.

    三种来源合并：
    1. 短期记忆 (deque)  — 包含在 memory_repo.retrieve() 返回中
    2. 长期记忆 (ChromaDB) — memory_repo.retrieve() 语义检索
    3. 反思记忆 (Reflection) — memory_repo.retrieve_reflections()

    Mock 模式下跳过 Chroma 检索，仅用本 tick 新产生的记忆。
    """
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
                if m.content and m.content not in seen:
                    contents.append(m.content)
                    seen.add(m.content)
        return contents

    memory_repo = get_repo(config, "memory")
    if not memory_repo:
        return []

    try:
        # 短期 + 长期记忆 / Short-term + Long-term
        retrieved = await memory_repo.retrieve(
            pc_id, query,
            top_k=top_k,
            memory_types=memory_types,
            periods=periods,
            entity_types=["pc", "actor"],
            current_tick=current_tick,
        )

        contents: list[str] = []
        seen: set[str] = set()

        # 本 tick 新产生的记忆（尚未落盘）/ Current tick memories not yet persisted
        if memories:
            current_mems = memories.get(pc_id, [])
            scored = sorted(
                current_mems,
                key=lambda m: score_memory(m.importance, m.tick, current_tick),
                reverse=True,
            )
            for m in scored[:top_k]:
                if m.content and m.content not in seen:
                    contents.append(m.content)
                    seen.add(m.content)

        # 反思记忆 / Reflections
        if include_reflections:
            reflections = await memory_repo.retrieve_reflections(
                pc_id, query, top_k=3, current_tick=current_tick
            )
            for m in reflections:
                c = getattr(m, "content", None)
                if c and c not in seen:
                    contents.append(c)
                    seen.add(c)

        # 短期 + 长期记忆 / Short-term + Long-term from retrieve()
        for m in retrieved:
            c = getattr(m, "content", None)
            if c and c not in seen:
                contents.append(c)
                seen.add(c)

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
