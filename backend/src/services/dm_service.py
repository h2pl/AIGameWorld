"""DM Service: State ↔ Engine adapter.

职责：读取 State → 构建 Request → 调用 Engine → 写回 State。
不直接访问 Repository（Engine 自己调，遵守 Service → Engine → Repository 分层）。
"""

from langchain_core.runnables.config import RunnableConfig

from ..engine.dm import dm as dm_engine
from ..graph.state import OverallState
from ..schemas.request import DMCreateRequest, DMNarrateRequest


def _get_llm(config: RunnableConfig | None):
    """从 configurable 中提取 LLMClient / Extract LLMClient from configurable."""
    if config and "configurable" in config:
        return config["configurable"].get("llm")
    return None


def _get_story_repo(config: RunnableConfig | None):
    """从 configurable 中提取 StoryRepo，透传给 Engine / Extract StoryRepo, pass to Engine."""
    if config and "configurable" in config:
        return config["configurable"].get("story_repo")
    return None


async def dm_create(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 1: DM 创造情境 / DM creates the scene."""
    result = await dm_engine.dm_create(
        DMCreateRequest(tick=state.get("tick", 0), plot_brief=state.get("plot_brief", "")),
        llm=_get_llm(config),
        story_repo=_get_story_repo(config),
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
        story_repo=_get_story_repo(config),
    )
    return {
        "narrative": result.narrative_out,
        "needs_reflection": state.get("tick", 0) % interval == 0 and state.get("tick", 0) > 0,
    }
