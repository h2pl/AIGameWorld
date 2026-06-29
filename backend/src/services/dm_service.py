"""DM Service: State ↔ Engine adapter."""

from langgraph.types import RunnableConfig

from ..schemas.request import DMCreateRequest, DMNarrateRequest
from ..schemas.response import DMNarrateResponse
from ..engine.dm import dm as dm_engine
from ..graph.state import OverallState
from ..domain import BranchPoint as DomainBranchPoint


def _get_llm(config: RunnableConfig | None):
    """从 configurable 中提取 LLMClient / Extract LLMClient from configurable."""
    if config and "configurable" in config:
        return config["configurable"].get("llm")
    return None


def _get_story_repo(config: RunnableConfig | None):
    """P2-4: 从 configurable 中提取 StoryRepo / Extract StoryRepo from configurable."""
    if config and "configurable" in config:
        return config["configurable"].get("story_repo")
    return None


async def dm_create(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 1: DM 创造情境 / DM creates the scene."""
    # P2-4: 从 StoryRepo 加载剧情线和未回收伏笔 / load arcs & active hooks from StoryRepo
    repo = _get_story_repo(config)
    story_arcs = await repo.load_arcs() if repo else []
    all_hooks = await repo.load_hooks() if repo else []
    active_hooks = [h for h in all_hooks if h.status == "planted"]

    result = await dm_engine.dm_create(
        DMCreateRequest(tick=state.get("tick", 0), plot_brief=state.get("plot_brief", "")),
        llm=_get_llm(config),
        story_arcs=story_arcs,
        active_hooks=active_hooks,
    )
    return {
        "dm_instructions": result.instructions_out,
        "plot_brief": result.plot_brief,
        "scene_direction": result.scene_direction,
    }


async def dm_narrate(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 6: DM 叙事 / DM narrates the scene."""
    interval = (config or {}).get("configurable", {}).get("reflection_interval", 5)
    result = await dm_engine.dm_narrate(
        DMNarrateRequest(
            tick=state.get("tick", 0),
            plot_brief=state.get("plot_brief", ""),
            dm_instructions=state.get("dm_instructions", []),
            scene_direction=state.get("scene_direction", {}),
            character_actions=state.get("character_actions", []),
        ),
        llm=_get_llm(config),
    )
    # P2-4: 把 branch_points 和 hooks_resolved 写回 StoryRepo /
    #       persist branch_points & hooks_resolved to StoryRepo
    repo = _get_story_repo(config)
    if repo:
        await _persist_narrate_results(repo, result, state.get("tick", 0))
    return {
        "narrative": result.narrative_out,
        "needs_reflection": state.get("tick", 0) % interval == 0 and state.get("tick", 0) > 0,
    }


async def _persist_narrate_results(
    repo, result: DMNarrateResponse, tick: int,
) -> None:
    """把 dm_narrate 产出写回 StoryRepo / Persist dm_narrate outputs to StoryRepo.

    - hooks_resolved: 标记对应伏笔为已回收 / mark hooks as resolved
    - branch_points: 追加到活跃主线剧情线 / append to active main arc
    """
    # 回收伏笔 / resolve hooks
    if result.hooks_resolved:
        hooks = await repo.load_hooks()
        for h in hooks:
            if h.id in result.hooks_resolved:
                h.status = "resolved"
                await repo.save_hook(h)

    # 分支点追加到活跃主线 / append branch points to active main arc
    if result.branch_points:
        arcs = await repo.load_arcs()
        active_main = next(
            (a for a in arcs if a.type == "main" and a.status != "completed"),
            None,
        )
        if active_main:
            for bp_data in result.branch_points:
                active_main.branching_points.append(DomainBranchPoint(
                    tick=tick,
                    decision_maker=bp_data.get("decision_maker", ""),
                    decision=bp_data.get("decision", ""),
                    consequence=bp_data.get("consequence", ""),
                ))
            await repo.save_arc(active_main)
