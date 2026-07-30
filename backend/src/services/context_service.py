"""Context Service——DM 上下文管理 / DM context management service.

职责：
1. build_dm_context() — 分层上下文组装（远期摘要 + 近期窗口 + Token 预算）
2. generate_dm_summary() — 每 N tick 记忆巩固（LLM 压缩，分 narrative/scene 两类）

设计原则：
- 远期摘要放开头，近期原文放结尾（对抗 Lost in the Middle）
- Token 预算裁剪：近期窗口优先保留，剩余预算给远期摘要
- 摘要分离：事件摘要(narrative) 与 场景摘要(scene) 独立压缩、独立注入
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
) -> dict:
    """组装 DM 上下文（分层优先级 + Token 预算）.

    返回结构化 dict：
    {
        "narrative_summaries": str,  # 远期事件摘要
        "scene_summaries": str,      # 远期场景摘要
        "recent_narratives": str,    # 近期事件原文
        "recent_scenes": str,        # 近期场景原文
    }
    """
    empty = {
        "narrative_summaries": "",
        "scene_summaries": "",
        "recent_narratives": "",
        "recent_scenes": "",
    }
    if is_mock(config):
        return empty

    dm_record_repo = get_repo(config, "dm_record")
    if not dm_record_repo:
        return empty

    try:
        # 1. 远期摘要（分类型）/ Distant summaries by type
        narrative_sums = await dm_record_repo.load_summaries(world_id, summary_type="narrative")
        scene_sums = await dm_record_repo.load_summaries(world_id, summary_type="scene")

        narrative_texts = [
            f"[tick {s.tick_start}-{s.tick_end}] {s.summary}"
            for s in narrative_sums
            if s.tick_end < current_tick
        ]
        scene_texts = [
            f"[tick {s.tick_start}-{s.tick_end}] {s.summary}"
            for s in scene_sums
            if s.tick_end < current_tick
        ]

        # 2. 近期窗口（分字段）/ Recent window by field
        records = await dm_record_repo.load_by_world(world_id, limit=_DM_RECENT_COUNT)
        recent_narr_lines: list[str] = []
        recent_scene_lines: list[str] = []
        for r in records:
            if r.tick >= current_tick:
                continue
            if r.dm_narrative:
                recent_narr_lines.append(f"[tick {r.tick}] {r.dm_narrative}")
            if r.plot_brief:
                recent_scene_lines.append(f"[tick {r.tick}] {r.plot_brief}")

        # 3. Token 预算裁剪 / Budget trimming
        recent_narr = "\n".join(recent_narr_lines)
        recent_scene = "\n".join(recent_scene_lines)
        summary_narr = "\n".join(narrative_texts)
        summary_scene = "\n".join(scene_texts)

        # 近期优先保留，剩余预算给远期摘要
        recent_total = len(recent_narr) + len(recent_scene)
        remaining = _DM_CONTEXT_BUDGET - recent_total
        summary_total = len(summary_narr) + len(summary_scene)
        if summary_total > remaining > 0:
            # 按比例截断 / Proportional trim
            ratio = remaining / summary_total
            summary_narr = _trim_block(summary_narr, int(len(summary_narr) * ratio))
            summary_scene = _trim_block(summary_scene, int(len(summary_scene) * ratio))
        elif remaining <= 0:
            summary_narr = ""
            summary_scene = ""

        return {
            "narrative_summaries": summary_narr,
            "scene_summaries": summary_scene,
            "recent_narratives": recent_narr,
            "recent_scenes": recent_scene,
        }
    except Exception:
        return empty


def _trim_block(block: str, max_chars: int) -> str:
    """截断文本块到指定长度，保留完整行 / Trim block to max_chars keeping complete lines."""
    if len(block) <= max_chars:
        return block
    trimmed = block[-max_chars:]
    nl = trimmed.find("\n")
    if nl > 0:
        trimmed = trimmed[nl + 1 :]
    return trimmed


async def generate_dm_summary(
    world_id: str,
    current_tick: int,
    config: RunnableConfig = None,
) -> None:
    """每 N tick 生成故事摘要（巩固）/ Generate story summary every N ticks.

    触发条件：current_tick % _DM_SUMMARY_INTERVAL == 0
    分别压缩 dm_narrative → narrative 摘要，plot_brief → scene 摘要。
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

    # 分离两类素材 / Separate source data by type
    narrative_records: list[dict] = []
    scene_records: list[dict] = []
    for r in records:
        if r.dm_narrative:
            narrative_records.append({"tick": r.tick, "text": r.dm_narrative})
        if r.plot_brief:
            scene_records.append({"tick": r.tick, "text": r.plot_brief})

    if not narrative_records and not scene_records:
        return

    # LLM 压缩 / LLM compression
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader
    from langchain_core.messages import HumanMessage

    from ..domain.story_summary import StorySummary
    from ..utils.helpers import get_llm
    from ..utils.logging import get_logger

    _logger = get_logger(__name__)
    llm = get_llm(config)
    if not llm:
        return

    _prompts_root = Path(__file__).parent.parent / "prompts"
    _env = Environment(loader=FileSystemLoader(_prompts_root), trim_blocks=True, lstrip_blocks=True)

    # 分别生成两类摘要 / Generate both summary types
    _type_templates = {
        "narrative": "dm/dm_summarize_narrative.jinja",
        "scene": "dm/dm_summarize_scene.jinja",
    }
    for summary_type, source_records in [
        ("narrative", narrative_records),
        ("scene", scene_records),
    ]:
        if not source_records:
            continue
        prompt = _env.get_template(_type_templates[summary_type]).render(
            tick_start=tick_start,
            tick_end=tick_end,
            records=source_records,
        )
        try:
            summary_text = await llm.call(
                purpose="reflection",
                tick_messages=[HumanMessage(content=prompt)],
            )
            if summary_text and summary_text.strip():
                summary = StorySummary(
                    world_id=world_id,
                    tick_start=tick_start,
                    tick_end=tick_end,
                    summary=summary_text.strip(),
                    summary_type=summary_type,
                )
                await dm_record_repo.insert_summary(summary)
                _logger.info(
                    "[dm_context] Generated %s summary tick %d-%d: %s",
                    summary_type,
                    tick_start,
                    tick_end,
                    summary_text[:50],
                )
        except Exception as e:
            _logger.warning("[dm_context] %s summary generation failed: %s", summary_type, e)
