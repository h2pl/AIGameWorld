"""DM Service: State ↔ Engine adapter.

Service 只管 State↔Request↔Response，所有外部资源 Engine 自己从 config 取。
"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import DMRecord, Scene, SceneObject
from ..engine.dm import dm_engine
from ..graph.state import OverallState
from ..schemas.request import DMCreateRequest, DMNarrateRequest
from ..utils.logging import trace_node


@trace_node("dm.create")
async def dm_create(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 1: DM 创造情境 / DM creates the situation."""
    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")
    prev_dm = state.get("dm_record")
    result = await dm_engine.dm_create(
        DMCreateRequest(
            tick=tick,
            plot_brief=prev_dm.plot_brief if prev_dm else "",
            world_id=world_id,
        ),
        config=config,
    )
    return {
        "dm_record": DMRecord(
            world_id=world_id,
            tick=tick,
            plot_brief=result.plot_brief,
            hints=result.hints,
            scene_id=result.scene_id,
            ext=result.ext or {},
        ),
    }


@trace_node("dm.narrate")
async def dm_narrate(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 6: DM 叙事——产出 narrative 写入 dm_record."""
    pcs = state.get("pcs", {})
    actors = state.get("actors", {})
    scene = state.get("scene")
    scene_objects = state.get("scene_objects", [])
    actions = state.get("actions", [])
    dm = state.get("dm_record")
    result = await dm_engine.dm_narrate(
        DMNarrateRequest(
            tick=state.get("tick", 0),
            world_id=state.get("world_id", ""),
            plot_brief=dm.plot_brief if dm else "",
            hints=dm.hints if dm else [],
            events=_summarize_events(state.get("tick_events", [])),
            scene=_scene_to_dict(scene),
            scene_objects=_objects_to_dicts(scene_objects),
            pcs={pc_id: pc.model_dump() for pc_id, pc in pcs.items()},
            actors={actor_id: actor.model_dump() for actor_id, actor in actors.items()},
            actions=[action.model_dump() for action in actions],
        ),
        config=config,
    )
    if dm:
        dm.dm_narrative = result.narrative_out
        return {"dm_record": dm}
    return {}


def _scene_to_dict(scene: Scene | None) -> dict:
    """把 Scene 领域模型转成 DMNarrateRequest 可接受的 dict."""
    if scene is None:
        return {}
    return scene.model_dump()


def _objects_to_dicts(scene_objects: list[SceneObject]) -> list[dict]:
    """把 SceneObject 列表转成 dict 列表."""
    return [obj.model_dump() for obj in scene_objects]


def _summarize_events(events: list) -> list[dict]:
    """把 TickEvent 列表转成 prompt 可读的摘要 / Convert events to prompt-friendly summary."""
    return [
        {
            "type": ev.type.value if hasattr(ev.type, "value") else str(ev.type),
            "description": str(ev.payload)[:200],
        }
        for ev in events
    ]
