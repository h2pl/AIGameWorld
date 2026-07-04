"""DM Service: State ↔ Engine adapter.

Service 只管 State↔Request↔Response，所有外部资源 Engine 自己从 config 取。
"""

from langchain_core.runnables.config import RunnableConfig

from ..engine.dm import dm_engine
from ..graph.state import OverallState
from ..schemas.request import DMCreateRequest, DMNarrateRequest
from ..utils.logging import trace_node


@trace_node("dm.create")
async def dm_create(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 1: DM 创造情境 / DM creates the scene_engine."""
    result = await dm_engine.dm_create(
        DMCreateRequest(
            tick=state.get("tick", 0),
            plot_brief=state.get("plot_brief", ""),
            world_id=state.get("world_id", ""),
        ),
        config=config,
    )
    return {
        "hints": result.hints,
        "plot_brief": result.plot_brief,
        "scene_id": result.scene_id,
        "_dm_ext": result.ext,  # LLM 原始输出，供 persist_tick 落 dm_records
    }


@trace_node("dm.narrate")
async def dm_narrate(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 6: DM 叙事 / DM narrates the scene_engine."""
    result = await dm_engine.dm_narrate(
        DMNarrateRequest(
            tick=state.get("tick", 0),
            world_id=state.get("world_id", ""),
            plot_brief=state.get("plot_brief", ""),
            hints=state.get("hints", []),
            tick_message_id=state.get("tick_message_id", ""),
        ),
        config=config,
    )
    return {
        "narrative": result.narrative_out,
    }
