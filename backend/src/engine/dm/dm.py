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

# prompts 统一在 src/prompts/ 下管理
_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))

# system prompt 从 jinja 模板加载，不再硬编码
_DM_SYSTEM_PROMPT = _PROMPTS.get_template("_persona_dm.jinja").render()


async def dm_create(req: DMCreateRequest, llm) -> DMCreateResponse:
    """Phase 1: DM 创造情境."""
    try:
        prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
            story_arcs=[],
            active_hooks=[],
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
    """Phase 6: DM 叙事."""
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
        return DMNarrateResponse(narrative_out=result.narrative)
    except Exception:
        logger.exception("dm_narrate failed, using fallback")
        return _fallback_narrate()


def _fallback_create() -> DMCreateResponse:
    return DMCreateResponse(
        instructions_out=[],
        plot_brief="平静的一天，没有特别事件。",
        scene_direction={"mood": "neutral"},
    )


def _fallback_narrate() -> DMNarrateResponse:
    return DMNarrateResponse(narrative_out="（DM 沉默了...）")
