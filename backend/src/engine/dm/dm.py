"""DM Engine——LLM 驱动的情境创造与叙事。per design/04-agent-layer.md §5."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import SystemMessage, HumanMessage

from ...schemas.request import DMCreateRequest, DMNarrateRequest
from ...schemas.response import DMCreateResponse, DMNarrateResponse
from ...schemas.llm_output import DMOutput, DMNarrativeSchema, SceneDirectionOutput
from ...domain.instruction import SceneDirection

logger = logging.getLogger(__name__)

# prompts 统一在 src/prompts/ 下管理 / prompts managed under src/prompts/
_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))

# system prompt 从 jinja 模板加载，不再硬编码 / system prompt loaded from jinja template
_DM_SYSTEM_PROMPT = _PROMPTS.get_template("_dm_system.jinja").render()


async def dm_create(
    req: DMCreateRequest,
    llm,
    story_arcs: list | None = None,
    active_hooks: list | None = None,
) -> DMCreateResponse:
    """Phase 1: DM 创造情境 / DM creates the scene.

    story_arcs/active_hooks 由 service 层从 StoryRepo 加载传入（P2-4），
    engine 层不直接访问 Repo / arcs & hooks loaded by service from StoryRepo.
    """
    if llm is None:
        return _fallback_create()
    try:
        prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
            story_arcs=story_arcs or [],
            active_hooks=active_hooks or [],
            recent_summary="",
            plot_brief_prev=req.plot_brief,
            pacing={},
        )
        result = await llm.call_structured(
            "dm_create",
            DMOutput,
            [SystemMessage(content=_DM_SYSTEM_PROMPT), HumanMessage(content=prompt)],
            fallback=lambda: DMOutput(
                plot_brief="平静的一天，没有特别事件。",
                scene_direction=SceneDirectionOutput(mood="neutral"),
            ),
        )
        result = _validate_dm_output(result)  # P2-6 业务护栏 / business guardrail
        direction = SceneDirection(
            featured_pcs=result.scene_direction.featured_pcs,
            featured_actors=result.scene_direction.featured_actors,
        )
        return DMCreateResponse(
            instructions_out=result.instructions,
            plot_brief=result.plot_brief,
            scene_direction=direction.model_dump(),
        )
    except Exception:
        logger.exception("dm_create failed, using fallback")
        return _fallback_create()


async def dm_narrate(req: DMNarrateRequest, llm) -> DMNarrateResponse:
    """Phase 6: DM 叙事 / DM narrates the scene."""
    if llm is None:
        return _fallback_narrate()
    try:
        prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief=req.plot_brief,
            character_actions=req.character_actions,
            events=[],
            combat_result=None,
            cast_changes=[],
        )
        result = await llm.call_structured(
            "dm_narrate",
            DMNarrativeSchema,
            [SystemMessage(content=_DM_SYSTEM_PROMPT), HumanMessage(content=prompt)],
            fallback=lambda: DMNarrativeSchema(narrative="（DM 沉默了...）"),
        )
        result = _validate_narrate_output(result)  # P2-6 业务护栏 / business guardrail
        return DMNarrateResponse(
            narrative_out=result.narrative,
            branch_points=[bp.model_dump() for bp in result.branch_points],
            hooks_resolved=result.hooks_resolved,
        )
    except Exception:
        logger.exception("dm_narrate failed, using fallback")
        return _fallback_narrate()


# ============================================================
# P2-6: 业务规则护栏 / Business rule guardrails
# ============================================================

_VALID_MOODS = {"neutral", "tense", "hopeful", "ominous", "mysterious"}


def _validate_dm_output(result: DMOutput) -> DMOutput:
    """DM 创造情境输出校验 + 修正 / Validate & fix DM create output.

    - mood 不在枚举内 → 修正为 neutral / fix invalid mood to neutral
    - instructions 为空 → 补默认 / fill default if empty
    - instructions 超过 4 条 → 截断 / truncate if exceeds 4
    """
    # mood 枚举校验 / mood enum validation
    if result.scene_direction.mood not in _VALID_MOODS:
        result.scene_direction.mood = "neutral"
    # instructions 数量边界 / instructions count boundary
    if not result.instructions:
        result.instructions = ["观察周围环境"]
    elif len(result.instructions) > 4:
        result.instructions = result.instructions[:4]
    return result


def _validate_narrate_output(result: DMNarrativeSchema) -> DMNarrativeSchema:
    """DM 叙事输出校验 / Validate DM narrate output.

    - narrative 为空 → 补占位文本 / fill placeholder if empty
    """
    if not result.narrative or not result.narrative.strip():
        result.narrative = "（DM 沉默了...）"
    return result


# ============================================================
# Fallback 降级输出 / Fallback degraded output
# ============================================================

def _fallback_create() -> DMCreateResponse:
    return DMCreateResponse(
        instructions_out=[],
        plot_brief="平静的一天，没有特别事件。",
        scene_direction={"mood": "neutral"},
    )


def _fallback_narrate() -> DMNarrateResponse:
    return DMNarrateResponse(narrative_out="（DM 沉默了...）", branch_points=[], hooks_resolved=[])
