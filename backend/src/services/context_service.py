"""Context Service——DM 上下文管理 / DM context management service.

职责：
1. build_dm_context() — 分层上下文组装（远期摘要 + 近期窗口 + Token 预算）
2. generate_dm_summary() — 每 N tick 记忆巩固（LLM 压缩）

设计原则：
- 远期摘要放开头，近期原文放结尾（对抗 Lost in the Middle）
- Token 预算裁剪：近期窗口优先保留，剩余预算给远期摘要
- 摘要约束：保留剧情转折+NPC+线索，丢弃环境描写+过渡叙述
"""

from langchain_core.runnables.config import RunnableConfig

from ..utils.helpers import get_repo, is_mock

# Token 预算常量 / Token budget constants
_DM_CONTEXT_BUDGET = 4000  # 总上下文 char 上限
_DM_RECENT_COUNT = 5  # 近期窗口保留条数
_DM_SUMMARY_INTERVAL = 10  # 每 N tick 生成一次摘要


async def build_dm_context(
    world_id: str,
    current_tick: int,
    config: RunnableConfig = None,
) -> str:
    """组装 DM 上下文（分层优先级 + Token 预算）.

    架构：
    1. 远期摘要 (story_summaries) — 低优先级，可截断
    2. 近期窗口 (最近 N 条 dm_records) — 中优先级，原文保留

    返回拼接后的上下文文本，供 dm_create / dm_narrate 注入 prompt。
    """
    if is_mock(config):
        return ""

    dm_record_repo = get_repo(config, "dm_record")
    if not dm_record_repo:
        return ""

    try:
        sections: list[str] = []

        # 1. 远期摘要 / Distant summaries (low priority, truncatable)
        summaries = await dm_record_repo.load_summaries(world_id)
        summary_texts = [
            f"[tick {s.tick_start}-{s.tick_end}] {s.summary}"
            for s in summaries
            if s.tick_end < current_tick
        ]

        # 2. 近期窗口 / Recent window (medium priority, verbatim)
        records = await dm_record_repo.load_by_world(world_id, limit=_DM_RECENT_COUNT)
        recent_texts: list[str] = []
        for r in records:
            if r.tick >= current_tick:
                continue
            parts: list[str] = []
            if r.plot_brief:
                parts.append(f"剧情：{r.plot_brief}")
            if r.dm_narrative:
                parts.append(f"叙事：{r.dm_narrative}")
            if parts:
                recent_texts.append(f"[tick {r.tick}] " + " | ".join(parts))

        # 3. Token 预算裁剪 / Budget trimming
        recent_block = "\n".join(recent_texts)
        summary_block = "\n".join(summary_texts)

        # 近期窗口优先保留，剩余预算给远期摘要
        remaining = _DM_CONTEXT_BUDGET - len(recent_block)
        if len(summary_block) > remaining > 0:
            # 从最远摘要开始截断 / Trim oldest summaries first
            summary_block = summary_block[-remaining:]
            # 截断到第一个完整行 / Cut to first complete line
            nl = summary_block.find("\n")
            if nl > 0:
                summary_block = summary_block[nl + 1 :]
        elif remaining <= 0:
            summary_block = ""

        if summary_block:
            sections.append(f"【远期脉络】\n{summary_block}")
        if recent_block:
            sections.append(f"【近期事件】\n{recent_block}")

        return "\n\n".join(sections)
    except Exception:
        return ""


async def generate_dm_summary(
    world_id: str,
    current_tick: int,
    config: RunnableConfig = None,
) -> None:
    """每 N tick 生成故事摘要（巩固）/ Generate story summary every N ticks.

    触发条件：current_tick % _DM_SUMMARY_INTERVAL == 0
    将过去 N 条 dm_records 压缩为 1 条 story_summary。
    """
    if current_tick <= 0 or current_tick % _DM_SUMMARY_INTERVAL != 0:
        return

    dm_record_repo = get_repo(config, "dm_record")
    if not dm_record_repo:
        return

    tick_start = current_tick - _DM_SUMMARY_INTERVAL + 1
    tick_end = current_tick

    # 检查是否已生成过 / Skip if already generated
    existing = await dm_record_repo.load_summaries(world_id)
    for s in existing:
        if s.tick_start == tick_start and s.tick_end == tick_end:
            return

    # 加载待压缩记录 / Load records to compress
    records = await dm_record_repo.load_range(world_id, tick_start, tick_end)
    if not records:
        return

    # 构造待压缩文本 / Build source text
    source_lines: list[str] = []
    for r in records:
        parts = []
        if r.plot_brief:
            parts.append(f"剧情：{r.plot_brief}")
        if r.dm_narrative:
            parts.append(f"叙事：{r.dm_narrative}")
        if parts:
            source_lines.append(f"[tick {r.tick}] " + " | ".join(parts))

    if not source_lines:
        return

    source_text = "\n".join(source_lines)

    # LLM 压缩 / LLM compression
    from langchain_core.messages import HumanMessage

    from ..domain.story_summary import StorySummary
    from ..utils.helpers import get_llm
    from ..utils.logging import get_logger

    _logger = get_logger(__name__)
    llm = get_llm(config)
    if not llm:
        return

    compress_prompt = (
        f"以下是游戏世界 tick {tick_start} 到 {tick_end} 的剧情记录：\n\n"
        f"{source_text}\n\n"
        "请将上述内容压缩为一段简洁的故事摘要（150字以内）。\n"
        "保留：剧情转折点、NPC名称与态度变化、未解决线索、队伍状态变化。\n"
        "丢弃：环境描写、过渡性叙述、重复信息。\n"
        "直接输出摘要文本，不要任何前缀。"
    )

    try:
        summary_text = await llm.call(
            purpose="reflection",
            tick_messages=[HumanMessage(content=compress_prompt)],
        )
        if summary_text and summary_text.strip():
            summary = StorySummary(
                world_id=world_id,
                tick_start=tick_start,
                tick_end=tick_end,
                summary=summary_text.strip(),
            )
            await dm_record_repo.insert_summary(summary)
            _logger.info(
                "[dm_context] Generated summary tick %d-%d: %s",
                tick_start,
                tick_end,
                summary_text[:50],
            )
    except Exception as e:
        _logger.warning("[dm_context] Summary generation failed: %s", e)
