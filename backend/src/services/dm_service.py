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
    """Phase 1: DM 创造情境 / DM creates the situation."""
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
        "_dm_ext": result.ext,
    }


@trace_node("dm.narrate")
async def dm_narrate(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 6: DM 叙事——产出 narrative 写入 state."""
    pcs = state.get("pcs", {})
    actors = state.get("actors", {})
    result = await dm_engine.dm_narrate(
        DMNarrateRequest(
            tick=state.get("tick", 0),
            world_id=state.get("world_id", ""),
            plot_brief=state.get("plot_brief", ""),
            hints=state.get("hints", []),
            events=_summarize_events(state.get("_pending_events", [])),
            scene=state.get("scene", {}),
            scene_objects=state.get("scene_objects", []),
            pcs={pc_id: pc.model_dump() for pc_id, pc in pcs.items()},
            actors={actor_id: actor.model_dump() for actor_id, actor in actors.items()},
            pending_actions=state.get("pending_actions", []),
        ),
        config=config,
    )
    return {"narrative": result.narrative_out}


def _summarize_events(events: list) -> list[dict]:
    """把 TickEvent 列表转成 prompt 可读的摘要 / Convert events to prompt-friendly summary."""
    return [
        {
            "type": ev.type.value if hasattr(ev.type, "value") else str(ev.type),
            "description": str(ev.payload)[:200],
        }
        for ev in events
    ]
