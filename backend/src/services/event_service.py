"""Event Service: 统一构造 TickEvent → 落盘 → 消息就绪."""

import logging
from typing import Any

from langchain_core.runnables.config import RunnableConfig

from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..utils.helpers import get_repo

logger = logging.getLogger("aw.svc")


def _dm_create_event(state: OverallState) -> TickEvent | None:
    """从 state 构造 dm_create 事件."""
    scene_id = state.get("scene_id", "")
    if not scene_id:
        return None
    return TickEvent(
        type=TickEventType.DM_CREATE,
        tick=state.get("tick", 0),
        tick_message_id=state.get("tick_message_id", ""),
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
        tick_message_id=state.get("tick_message_id", ""),
        payload={
            "scene_id": scene_id,
            "scene": scene,
        },
    )


_EVENT_TYPE_MAP: dict[str, TickEventType] = {
    "talk": TickEventType.PC_TALK,
    "interact": TickEventType.PC_INTERACT,
    "search": TickEventType.PC_INTERACT,
}


def _action_events(state: OverallState) -> list[TickEvent]:
    """从 pending_actions 构造 character_talk / character_interact 事件."""
    pending_actions: list[dict[str, Any]] = state.get("pending_actions", [])
    if not pending_actions:
        return []
    tick = state.get("tick", 0)
    msg_id = state.get("tick_message_id", "")
    # 按 order 排序 / Sort by order
    sorted_actions = sorted(pending_actions, key=lambda a: a.get("order", 0))
    events: list[TickEvent] = []
    for action in sorted_actions:
        action_type = action.get("action_type", "")
        event_type = _EVENT_TYPE_MAP.get(action_type)
        if event_type is None:
            continue
        result = action.get("result", {}) or {}
        events.append(
            TickEvent(
                type=event_type,
                tick=tick,
                tick_message_id=msg_id,
                payload={
                    "order": action.get("order"),
                    "pc_id": action.get("pc_id", ""),
                    "action_type": action_type,
                    "target_id": action.get("target_id", ""),
                    "target_type": action.get("target_type", ""),
                    "result": result,
                },
            )
        )
    return events


def _pick(*evs: TickEvent | None) -> list[TickEvent]:
    """过滤 None，返回有效事件列表."""
    return [e for e in evs if e is not None]


async def flush_events(state: OverallState, config: RunnableConfig = None) -> dict:
    """从 state 各阶段产出统一构造 TickEvent → 写 tick_events → 标记消息可消费."""
    tick_message_id = state.get("tick_message_id", "")
    if not tick_message_id:
        return {}

    tick = state.get("tick", 0)
    events = [
        *_pick(_dm_create_event(state), _scene_event(state)),
        *_action_events(state),
    ]

    event_repo = get_repo(config, "event")
    if events and event_repo:
        await event_repo.insert_tick_events(tick_message_id, tick, events)
        logger.info(
            "[event] flushed tick=%s tick_message_id=%s count=%d",
            tick,
            tick_message_id,
            len(events),
        )

    message_repo = get_repo(config, "message")
    if message_repo:
        await message_repo.mark_ready(tick_message_id, tick)
        logger.info("[event] message ready tick=%s tick_message_id=%s", tick, tick_message_id)
    return {}
