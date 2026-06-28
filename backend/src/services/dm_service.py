"""DM Service: State ↔ Engine adapter."""

from langgraph.types import RunnableConfig

from ..schemas.request import DMCreateRequest, DMNarrateRequest
from ..engine.dm import dm as dm_engine
from ..graph.state import OverallState


def _get_llm(config: RunnableConfig | None):
    """从 configurable 中提取 LLMClient."""
    if config and "configurable" in config:
        return config["configurable"].get("llm")
    return None


async def dm_create(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 1: DM 创造情境."""
    result = await dm_engine.dm_create(
        DMCreateRequest(tick=state.get("tick", 0), plot_brief=state.get("plot_brief", "")),
        llm=_get_llm(config),
    )
    return {
        "dm_instructions": result.instructions_out,
        "plot_brief": result.plot_brief,
        "scene_direction": result.scene_direction,
    }


async def dm_narrate(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 6: DM 叙事."""
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
    return {
        "narrative": result.narrative_out,
        "needs_reflection": state.get("tick", 0) % interval == 0 and state.get("tick", 0) > 0,
    }
