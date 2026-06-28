"""DM Service: State ↔ Engine adapter."""

from ..schemas.request import DMCreateRequest, DMNarrateRequest
from ..engine.dm.dm import dm_create as _dm_create, dm_narrate as _dm_narrate
from ..graph.state import OverallState


async def dm_create(state: OverallState, agent=None) -> dict:
    """Phase 1: DM 创造情境."""
    result = await _dm_create(
        DMCreateRequest(tick=state.get("tick", 0), plot_brief=state.get("plot_brief", "")),
        agent=agent,
    )
    return {
        "dm_instructions": result.instructions_out,
        "plot_brief": result.plot_brief,
        "scene_direction": result.scene_direction,
    }


async def dm_narrate(state: OverallState, agent=None) -> dict:
    """Phase 6: DM 叙事."""
    result = await _dm_narrate(
        DMNarrateRequest(
            tick=state.get("tick", 0),
            plot_brief=state.get("plot_brief", ""),
            dm_instructions=state.get("dm_instructions", []),
            scene_direction=state.get("scene_direction", {}),
            character_actions=state.get("character_actions", []),
        ),
        agent=agent,
    )
    return {
        "narrative": result.narrative_out,
        "needs_reflection": state.get("tick", 0) % 5 == 0,
    }
