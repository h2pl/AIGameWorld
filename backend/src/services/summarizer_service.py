"""Summarizer Service——LLM 驱动的 tick 总结叙事 / LLM-driven tick narrative summary.

在 events 生成后，根据所有事件生成一段 DM 叙事，并追加 dm_narrative 事件。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..schemas.llm_output import DMNarrativeSchema
from ..utils.helpers import get_llm
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


@trace_node("summarizer.narrate")
async def narrate(state: OverallState, config: RunnableConfig = None) -> dict:
    """根据本 tick 已生成事件生成叙事，追加 dm_narrative 事件到 _pending_events."""
    events = state.get("_pending_events", [])
    if not events:
        return {"narrative": "", "_pending_events": events}

    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")

    narrative = await _generate_narrative(
        plot_brief=plot_brief,
        hints=hints,
        events=events,
        config=config,
    )

    narrative_event = TickEvent(
        type=TickEventType.DM_NARRATIVE,
        tick=tick,
        world_id=world_id,
        payload={"text": narrative},
    )
    events.append(narrative_event)
    logger.info("[summarizer] generated narrative tick=%s len=%d", tick, len(narrative))
    return {"narrative": narrative, "_pending_events": events}


async def _generate_narrative(
    plot_brief: str,
    hints: list[str],
    events: list,
    config: RunnableConfig = None,
) -> str:
    """调用 LLM 生成 tick 叙事 / Generate tick narrative via LLM."""
    llm = get_llm(config)
    if llm is None:
        return _fallback_narrative(events)

    ctx = {
        "plot_brief": plot_brief,
        "hints": hints,
        "events": [_event_summary(ev) for ev in events],
    }
    try:
        system = _PROMPTS.get_template("dm/_dm_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(**ctx)
    except Exception:
        logger.exception("[summarizer] prompt render failed")
        return _fallback_narrative(events)

    try:
        result = await llm.call_structured(
            "dm_narrate",
            DMNarrativeSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: DMNarrativeSchema(narrative=_fallback_narrative(events)),
        )
        return result.narrative or _fallback_narrative(events)
    except Exception:
        logger.exception("[summarizer] narrative generation failed")
        return _fallback_narrative(events)


def _event_summary(ev) -> dict:
    """把事件对象转成 prompt 可读的摘要 / Convert event to prompt summary."""
    payload = ev.payload if hasattr(ev, "payload") else ev.get("payload", {})
    return {
        "type": ev.type if hasattr(ev, "type") else ev.get("type", "?"),
        "description": str(payload)[:200],
    }


def _fallback_narrative(events: list) -> str:
    """LLM 不可用时降级叙事 / Fallback narrative."""
    if not events:
        return "什么也没有发生。"
    types = [e.type if hasattr(e, "type") else e.get("type", "?") for e in events]
    return f"本 tick 发生了：{', '.join(types)}。"


async def summarize(state: dict, config: RunnableConfig = None) -> dict:
    """向后兼容：压缩 tick_events → summary_text（反射阶段仍可能使用）/ Back-compat summarizer."""
    events = state.get("tick_events", state.get("events", []))
    character_count = state.get("character_count", 0)

    llm = get_llm(config)
    if llm is None or not events:
        return {"summary_compressed": False, "tick_events": events}

    prompt = _PROMPTS.get_template("reflection/summarize.jinja").render(
        events=events, event_count=len(events), char_count=character_count
    )
    try:
        result = await llm.call_structured(
            "summarize", None, [{"role": "user", "content": prompt}], fallback=dict
        )
        summary = result.get("summary", "")
        return {
            "summary_compressed": bool(summary),
            "summary_text": summary,
            "tick_events": events,
        }
    except Exception:
        logger.exception("[summarizer] summarize failed")
        return {"summary_compressed": False, "tick_events": events}
