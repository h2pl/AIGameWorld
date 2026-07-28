"""Memory Service——为各引擎提供按需记忆注入 / Memory injection service for engines.

三种记忆类型，service 层负责编排：
1. 短期记忆 (Short-Term)：deque 窗口，recency 优先
2. 长期记忆 (Long-Term)：ChromaDB 语义召回 → SQLite 补全 → 精排
3. 反思记忆 (Reflection)：ChromaDB 语义检索
"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import Memory
from ..repository.memory_repo import score_memory
from ..utils.helpers import get_repo, is_mock


async def compress_context(query: str, raw_memories: list[str], llm) -> list[str]:
    """如果长上下文过长，调用轻量级模型对记忆进行压缩提炼 / Compress long memory contexts."""
    if not raw_memories or not llm:
        return raw_memories

    total_len = sum(len(m) for m in raw_memories)
    if len(raw_memories) <= 3 or total_len < 1000:
        return raw_memories

    prompt = f"当前情境或意图：{query}\n\n"
    prompt += "以下是从角色记忆库中检索到的相关片段：\n"
    for i, m in enumerate(raw_memories):
        prompt += f"[{i+1}] {m}\n"
    prompt += "\n请根据当前情境，将上述记忆压缩提炼成3-5条最核心的线索。过滤掉不相关的冗余细节。直接输出要点，不要任何寒暄。"

    from langchain_core.messages import HumanMessage

    try:
        compressed_text = await llm.call(
            purpose="reflection",
            tick_messages=[HumanMessage(content=prompt)],
        )
        if compressed_text:
            return [line.strip("- ") for line in compressed_text.split("\n") if line.strip()]
    except Exception as e:
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"[memory_service] Context compression failed: {e}")

    return raw_memories


async def retrieve_memories(
    pc_id: str,
    query: str,
    config: RunnableConfig = None,
    top_k: int = 5,
    memory_types: list[str] | None = None,
    periods: list[str] | None = None,
    include_reflections: bool = True,
    current_tick: int = 0,
) -> list[str]:
    """检索角色相关记忆，按综合分数排序返回内容文本.

    service 层编排三种记忆来源，repo 层只提供原子方法：
    1. 短期记忆：repo.get_short_term() — deque 窗口
    2. 长期记忆：repo.search_long_term_vector() → repo.fetch_long_term_sqlite()
    3. 反思记忆：repo.retrieve_reflections()
    """
    if is_mock(config):
        return []

    memory_repo = get_repo(config, "memory")
    if not memory_repo:
        return []

    try:
        # 1. 短期记忆 / Short-term from deque
        short = memory_repo.get_short_term(pc_id)
        # 构建 semantic_scores：短期记忆无语义分
        semantic_scores: dict[str, float] = {}

        # 2. 长期记忆 / Long-term: ChromaDB 语义召回 → SQLite 补全
        vector_results = memory_repo.search_long_term_vector(pc_id, query, top_k=top_k * 3)
        candidate_ids = set()
        for r in vector_results:
            mem_id = r["meta"].get("id", "")
            if mem_id:
                candidate_ids.add(mem_id)
                distance = r.get("distance", 1.0)
                semantic_scores[mem_id] = max(0.0, 1.0 - (distance / 2.0))

        long_term: list[Memory] = []
        if candidate_ids:
            long_term = await memory_repo.fetch_long_term_sqlite(list(candidate_ids))

        # 3. 合并 + 过滤 / Merge + filter
        def _matches(m: Memory) -> bool:
            return (
                (not memory_types or m.memory_type in memory_types)
                and (not periods or m.period in periods)
                and m.entity_type in ("pc", "actor")
            )

        seen: set[str] = set()
        merged: list[Memory] = []
        for m in short + long_term:
            if m.id not in seen and _matches(m):
                merged.append(m)
                seen.add(m.id)

        # 4. 精排 / Re-rank
        def _score(m: Memory) -> float:
            base = score_memory(m.importance, m.tick, current_tick)
            if m.period == "short_term":
                return base * 1.2
            if m.id in semantic_scores:
                return base + base * semantic_scores[m.id] * 1.5
            return base

        merged.sort(key=_score, reverse=True)
        merged = merged[:top_k]

        contents: list[str] = []
        for m in merged:
            if m.content and m.content not in contents:
                contents.append(m.content)

        # 5. 反思记忆 / Reflections
        if include_reflections:
            reflections = await memory_repo.retrieve_reflections(
                pc_id, query, top_k=3, current_tick=current_tick
            )
            for m in reflections:
                c = getattr(m, "content", None)
                if c and c not in contents:
                    contents.append(c)

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
