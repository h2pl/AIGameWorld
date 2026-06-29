"""DM Engine——LLM 驱动的情境创造与叙事。per design/04-agent-layer.md §5.

分层遵循 Service → Engine → Repository 调用链：
Service 负责 State↔Request 适配，Engine 负责业务逻辑 + 调用 Repository。
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from ...domain import BranchPoint as DomainBranchPoint
from ...domain.instruction import SceneDirection
from ...schemas.llm_output import DMNarrativeSchema, DMOutput, SceneDirectionOutput
from ...schemas.request import DMCreateRequest, DMNarrateRequest
from ...schemas.response import DMCreateResponse, DMNarrateResponse

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
_DM_SYSTEM_PROMPT = _PROMPTS.get_template("_dm_system.jinja").render()


# ============================================================
# Phase 1: 创造情境 / Create scene
# ============================================================


async def dm_create(
    req: DMCreateRequest,
    llm,
    story_repo=None,  # P2-4: StoryRepo，Engine 自己调 / StoryRepo, called by Engine
) -> DMCreateResponse:
    """Phase 1: DM 创造情境 / DM creates the scene.

    Engine 直接从 StoryRepo 加载剧情线和伏笔（Service→Engine→Repository 分层）。
    """
    if llm is None:
        return DMCreateResponse(
            instructions_out=[],
            plot_brief="平静的一天，没有特别事件。",
        )
    try:
        # 从 Repository 加载上下文 / load context from Repository
        story_arcs = await story_repo.load_arcs() if story_repo else []
        all_hooks = await story_repo.load_hooks() if story_repo else []
        active_hooks = [h for h in all_hooks if h.status == "planted"]

        prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
            story_arcs=story_arcs,
            active_hooks=active_hooks,
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
        result = _validate_dm_output(result)
        direction = SceneDirection(
            type="scene_direction",
            featured_pcs=result.scene_direction.featured_pcs,
            featured_actors=result.scene_direction.featured_actors,
            actor_motivations=result.scene_direction.actor_motivations,
        )
        return DMCreateResponse(
            instructions_out=result.instructions,
            plot_brief=result.plot_brief,
            scene_direction=direction.model_dump(),
        )
    except Exception:
        logger.exception("dm_create failed, using fallback")
        return DMCreateResponse(
            instructions_out=[],
            plot_brief="平静的一天，没有特别事件。",
            scene_direction={},
            errors=["dm_create LLM 调用失败，使用降级输出"],
        )


# ============================================================
# Phase 6: 叙事 / Narrate
# ============================================================


async def dm_narrate(
    req: DMNarrateRequest,
    llm,
    story_repo=None,  # P2-4: StoryRepo，Engine 自己调 / StoryRepo, called by Engine
) -> DMNarrateResponse:
    """Phase 6: DM 叙事 / DM narrates the scene.

    Engine 自己把 branch_points/hooks_resolved 写回 StoryRepo（Service→Engine→Repository）。
    """
    if llm is None:
        return DMNarrateResponse(narrative_out="（DM 沉默了...）")
    try:
        prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief=req.plot_brief,
            character_actions=req.character_actions,
            events=[],  # TODO: Phase 3/4 接通后从 State 读取实际事件
            combat_result=None,  # TODO: Phase 4 战斗引擎接通后从 State 读取
            cast_changes=[],  # TODO: Phase 5 状态合并后从 State 读取角色变动
        )
        result = await llm.call_structured(
            "dm_narrate",
            DMNarrativeSchema,
            [SystemMessage(content=_DM_SYSTEM_PROMPT), HumanMessage(content=prompt)],
            fallback=lambda: DMNarrativeSchema(narrative="（DM 沉默了...）"),
        )
        result = _validate_narrate_output(result)
        response = DMNarrateResponse(
            narrative_out=result.narrative,
            branch_points=[bp.model_dump() for bp in result.branch_points],
            hooks_resolved=result.hooks_resolved,
        )
        # 写回 Repository / persist to Repository
        if story_repo:
            await _persist_narrate_results(story_repo, response, req.tick)
        return response
    except Exception:
        logger.exception("dm_narrate failed, using fallback")
        return DMNarrateResponse(
            narrative_out="（DM 沉默了...）",
            branch_points=[],
            hooks_resolved=[],
            errors=["dm_narrate LLM 调用失败，使用降级输出"],
        )


# ============================================================
# P2-6: 业务规则护栏 / Business rule guardrails
# ============================================================

_VALID_MOODS = {"neutral", "tense", "hopeful", "ominous", "mysterious"}


def _validate_dm_output(result: DMOutput) -> DMOutput:
    """DM 创造情境输出校验 + 修正 / Validate & fix DM create output."""
    if result.scene_direction.mood not in _VALID_MOODS:
        result.scene_direction.mood = "neutral"
    if not result.instructions:
        result.instructions = ["观察周围环境"]
    elif len(result.instructions) > 4:
        result.instructions = result.instructions[:4]
    return result


def _validate_narrate_output(result: DMNarrativeSchema) -> DMNarrativeSchema:
    """DM 叙事输出校验 / Validate DM narrate output."""
    if not result.narrative or not result.narrative.strip():
        result.narrative = "（DM 沉默了...）"
    return result


# ============================================================
# P2-4: Repository 写回 / Persist to Repository
# ============================================================


async def _persist_narrate_results(
    story_repo,
    result: DMNarrateResponse,
    tick: int,
) -> None:
    """把 dm_narrate 产出写回 StoryRepo / Persist dm_narrate outputs to StoryRepo.

    - hooks_resolved: 标记对应伏笔为已回收 / mark hooks as resolved
    - branch_points: 追加到活跃主线剧情线 / append to active main arc
    """
    if result.hooks_resolved:
        hooks = await story_repo.load_hooks()
        for h in hooks:
            if h.id in result.hooks_resolved:
                h.status = "resolved"
                await story_repo.save_hook(h)

    if result.branch_points:
        arcs = await story_repo.load_arcs()
        active_main = next(
            (a for a in arcs if a.type == "main" and a.status != "completed"),
            None,
        )
        if active_main:
            for bp_data in result.branch_points:
                active_main.branching_points.append(
                    DomainBranchPoint(
                        tick=tick,
                        decision_maker=bp_data.get("decision_maker", ""),
                        decision=bp_data.get("decision", ""),
                        consequence=bp_data.get("consequence", ""),
                    )
                )
            await story_repo.save_arc(active_main)



