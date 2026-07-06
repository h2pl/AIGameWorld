"""Event Service: 从 state 构造 TickEvent，不负责持久化."""

from typing import Any

from langchain_core.runnables.config import RunnableConfig  # noqa: F401  # type annotation

from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _dm_create_event(state: OverallState) -> TickEvent | None:
    """从 state 构造 dm_create 事件."""
    scene_id = state.get("scene_id", "")
    if not scene_id:
        return None
    return TickEvent(
        type=TickEventType.DM_CREATE,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "plot_brief": state.get("plot_brief", ""),
            "hints": state.get("hints", []),
        },
    )


def _scene_event(state: OverallState) -> TickEvent | None:
    """构造 scene_setup 事件。

    scene/objects 来自 scene_info（静态数据），PC/Actor 坐标从 state maps 获取。
    """
    scene_info: dict[str, Any] = state.get("scene_info", {}) or {}
    scene: dict[str, Any] = scene_info.get("scene", {}) or {}
    scene_id = scene.get("id", "")
    if not scene_id:
        return None
    # PC/Actor 从 state maps 获取（最新坐标），不从 scene_info["pcs"]/["actors"] 读
    pc_state_map = state.get("pc_state_map", {})
    actor_state_map = state.get("actor_state_map", {})
    pcs = [{**info, "id": pid} for pid, info in pc_state_map.items()]
    actors = [{**info, "id": aid} for aid, info in actor_state_map.items()]
    return TickEvent(
        type=TickEventType.SCENE_SETUP,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "scene": scene,
            "pcs": pcs,
            "actors": actors,
            "scene_objects": scene_info.get("scene_objects", []),
        },
    )


_EVENT_TYPE_MAP: dict[str, TickEventType] = {
    "talk": TickEventType.PC_TALK,
    "interact": TickEventType.PC_INTERACT,
    "explore": TickEventType.PC_EXPLORE,
}


def _action_events(state: OverallState) -> list[TickEvent]:
    """从 pending_actions 构造 character_talk / character_explore 等事件."""
    pending_actions: list[dict[str, Any]] = state.get("pending_actions", [])
    if not pending_actions:
        return []
    tick = state.get("tick", 0)
    sorted_actions = sorted(pending_actions, key=lambda a: a.get("order", 0))
    events: list[TickEvent] = []
    for action in sorted_actions:
        action_type = action.get("action_type", "")
        event_type = _EVENT_TYPE_MAP.get(action_type)
        if event_type is None:
            continue
        raw_result = action.get("result", {}) or {}
        # 兼容 Pydantic 模型和 dict / Supports both model and dict
        if isinstance(raw_result, dict):
            result = raw_result
        else:
            result = raw_result.model_dump() if hasattr(raw_result, "model_dump") else {}
        pc_id = action.get("pc_id", "")
        pc_name = (state.get("pc_state_map", {}).get(pc_id, {}) or {}).get("name", pc_id)
        payload = {
            "order": action.get("order"),
            "pc_id": pc_id,
            "pc_name": pc_name,
            "action_type": action_type,
            "target_id": action.get("target_id", ""),
            "target_type": action.get("target_type", ""),
            "result": result,
        }
        if event_type == TickEventType.PC_EXPLORE:
            payload["waypoints"] = result.get("waypoints", [])
            payload["explore_record"] = result.get("explore_record", "")
        if event_type == TickEventType.PC_TALK:
            payload["waypoints"] = result.get("waypoints", [])
        if event_type == TickEventType.PC_INTERACT:
            payload["waypoints"] = result.get("waypoints", [])
            payload["narration"] = result.get("narration", "")
        events.append(
            TickEvent(
                type=event_type,
                tick=tick,
                world_id=state.get("world_id", ""),
                payload=payload,
            )
        )
    return events


def _pick(*evs: TickEvent | None) -> list[TickEvent]:
    """过滤 None，返回有效事件列表."""
    return [e for e in evs if e is not None]


def flush_events(state: OverallState, config: RunnableConfig = None) -> dict:
    """从 state 各阶段产出统一构造 TickEvent 列表，存入 _pending_events 供 data_service 落盘."""
    events = [
        *_pick(_dm_create_event(state), _scene_event(state)),
        *_action_events(state),
    ]
    tick = state.get("tick", 0)
    logger.info("[service] flushed events tick=%s count=%d", tick, len(events))
    return {"_pending_events": events}


def emit_narrative_event(state: OverallState, config: RunnableConfig = None) -> dict:
    """将 state.narrative 转为 DM_NARRATIVE 事件追加到 _pending_events."""
    narrative = state.get("narrative", "")
    events = list(state.get("_pending_events", []))
    if narrative:
        events.append(
            TickEvent(
                type=TickEventType.DM_NARRATIVE,
                tick=state.get("tick", 0),
                world_id=state.get("world_id", ""),
                payload={"text": narrative},
            )
        )
    return {"_pending_events": events}
