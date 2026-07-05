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
    """从 scene_info 构造 scene_setup 事件."""
    scene_info: dict[str, Any] = state.get("scene_info", {}) or {}
    scene: dict[str, Any] = scene_info.get("scene", {}) or {}
    scene_id = scene.get("id", "")
    if not scene_id:
        return None
    return TickEvent(
        type=TickEventType.SCENE_SETUP,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "scene": scene,
            "pcs": scene_info.get("pcs", []),
            "actors": scene_info.get("actors", []),
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
        result = action.get("result", {}) or {}
        payload = {
            "order": action.get("order"),
            "pc_id": action.get("pc_id", ""),
            "action_type": action_type,
            "target_id": action.get("target_id", ""),
            "target_type": action.get("target_type", ""),
            "result": result,
        }
        if event_type == TickEventType.PC_EXPLORE:
            payload["waypoints"] = result.get("waypoints", [])
        if event_type == TickEventType.PC_TALK:
            payload["waypoints"] = result.get("waypoints", [])
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
