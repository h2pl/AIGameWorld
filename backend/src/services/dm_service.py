"""DM Service: State ↔ Engine adapter.

Service 只管 State↔Request↔Response，所有外部资源 Engine 自己从 config 取。
"""

from langchain_core.runnables.config import RunnableConfig

from ..engine.dm import dm as dm_engine
from ..graph.state import OverallState
from ..schemas.request import DMCreateRequest, DMNarrateRequest


async def dm_create(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 1: DM 创造情境 / DM creates the scene."""
    result = await dm_engine.dm_create(
        DMCreateRequest(tick=state.get("tick", 0), plot_brief=state.get("plot_brief", "")),
        config=config,
    )
    return {
        "dm_instructions": result.instructions_out,
        "plot_brief": result.plot_brief,
        "scene_direction": result.scene_direction,
        "errors": result.errors,
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
        config=config,
    )
    return {
        "narrative": result.narrative_out,
        "branch_points": result.branch_points,
        "hooks_resolved": result.hooks_resolved,
        "errors": result.errors,
        "needs_reflection": state.get("tick", 0) % interval == 0 and state.get("tick", 0) > 0,
    }
