"""DM Service: State ↔ Engine adapter."""

from ..schemas.request import DMCreateRequest, DMNarrateRequest
from ..engine.dm import dm as dm_engine
from ..graph.state import OverallState


async def dm_create(state: OverallState, llm=None) -> dict:
    """Phase 1: DM 创造情境."""
    result = await dm_engine.dm_create(
        DMCreateRequest(tick=state.get("tick", 0), plot_brief=state.get("plot_brief", "")),
        llm=llm,
    )
    return {
        "dm_instructions": result.instructions_out,
        "plot_brief": result.plot_brief,
        "scene_direction": result.scene_direction,
    }


async def dm_narrate(state: OverallState, llm=None, reflection_interval: int = 5) -> dict:
    """Phase 6: DM 叙事."""
    result = await dm_engine.dm_narrate(
        DMNarrateRequest(
            tick=state.get("tick", 0),
            plot_brief=state.get("plot_brief", ""),
            dm_instructions=state.get("dm_instructions", []),
            scene_direction=state.get("scene_direction", {}),
            character_actions=state.get("character_actions", []),
        ),
        llm=llm,
    )
    return {
        "narrative": result.narrative_out,
        "needs_reflection": state.get("tick", 0) % reflection_interval == 0 and state.get("tick", 0) > 0,
    }
