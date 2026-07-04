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
            "pc_positions": scene_info.get("pc_positions", {}),
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
    scene_info: dict[str, Any] = state.get("scene_info", {}) or {}
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
            payload["final_x"] = result.get("final_x", 0)
            payload["final_y"] = result.get("final_y", 0)
            payload["start_x"] = result.get("start_x", 0)
            payload["start_y"] = result.get("start_y", 0)
        if event_type == TickEventType.PC_TALK:
            pc_id = action.get("pc_id", "")
            target_id = action.get("target_id", "")
            payload["pc_position"] = _get_char_position(
                pc_id, scene_info, state.get("pc_state_map", {})
            )
            payload["target_position"] = _get_char_position(
                target_id, scene_info, state.get("pc_state_map", {})
            )
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


def _get_char_position(
    char_id: str,
    scene_info: dict[str, Any],
    pc_state_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, int]:
    """获取角色坐标——优先 pc_state_map（tick 内最新），其次 scene_info / 
    Get character position — pc_state_map first (in-tick latest), then scene_info."""
    if not char_id:
        return {"x": 0, "y": 0}
    # tick 内坐标优先 / In-tick position takes priority
    if pc_state_map and char_id in pc_state_map:
        info = pc_state_map[char_id]
        return {"x": info.get("position_x", 0), "y": info.get("position_y", 0)}
    # fallback: scene_info / Fallback to scene_info
    positions = scene_info.get("pc_positions", {})
    if char_id in positions:
        pos = positions[char_id]
        return {"x": pos.get("x", 0), "y": pos.get("y", 0)}
    for lst_key in ("pcs", "actors"):
        for ch in scene_info.get(lst_key, []):
            if ch.get("id") == char_id:
                return {"x": ch.get("position_x", 0), "y": ch.get("position_y", 0)}
    return {"x": 0, "y": 0}


def flush_events(state: OverallState, config: RunnableConfig = None) -> dict:
    """从 state 各阶段产出统一构造 TickEvent 列表，存入 _pending_events 供 data_service 落盘."""
    events = [
        *_pick(_dm_create_event(state), _scene_event(state)),
        *_action_events(state),
    ]
    tick = state.get("tick", 0)
    logger.info("[service] flushed events tick=%s count=%d", tick, len(events))
    return {"_pending_events": events}
