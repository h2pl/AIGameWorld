"""DM Service: State ↔ Engine adapter."""
from typing import Any

from ..schemas.request import DMCreateRequest, DMNarrateRequest
from ..engine.dm.dm import dm_create as _dm_create, dm_narrate as _dm_narrate
from ..graph.state import OverallState


def dm_create(state: OverallState) -> dict[str, Any]:
    """Phase 1: DM 创造情境."""
    result = _dm_create(DMCreateRequest(
        tick=state.get("tick", 0),
        plot_brief=state.get("plot_brief", ""),
    ))
    return {
        "dm_instructions": result.instructions_out,
        "plot_brief": result.plot_brief,
        "scene_direction": result.scene_direction,
    }


def dm_narrate(state: OverallState) -> dict[str, Any]:
    """Phase 6: DM 叙事."""
    result = _dm_narrate(DMNarrateRequest(
        tick=state.get("tick", 0),
        plot_brief=state.get("plot_brief", ""),
        dm_instructions=state.get("dm_instructions", []),
        scene_direction=state.get("scene_direction", {}),
        character_actions=state.get("character_actions", []),
    ))
    return {"narrative": result.narrative_out, "needs_reflection": state.get("tick", 0) % 5 == 0}
