"""Event Service: State ↔ Repo adapter——统一构造 + 落盘事件 + 消息就绪标记.

主图各阶段只把需要发给前端的原始信息写进 state（scene_service 写
scene_info，character_service.act 写 pending_actions（每项统一格式为
{order, action_type, target_id, target_type, result}），dm_service.dm_narrate
写 narrative），不构造事件、也不直接碰 event_repo/message_repo；本服务是
主图最后一步，从这些 state 字段中收集原始结果，统一转换成
{"type", "payload"} 事件记录、写入 tick_events 表，并在事件落盘后把消息
标记为可消费（pending），供前端轮询拉取 /
Each phase of the main graph only writes the raw info that needs to reach
the frontend into state (scene_service writes scene_info,
character_service.act writes pending_actions — each item uniformly shaped as
{order, action_type, target_id, target_type, result} — dm_service.dm_narrate
writes narrative) — none of them build event records or touch
event_repo/message_repo directly. This service is the last step of the main
tick graph: it gathers raw results from those state fields, converts them
into {"type", "payload"} event records, persists them to the tick_events
table, and — once events are persisted — marks the message consumable
(pending) so the frontend can poll it.
"""

import logging
from typing import Any

from langchain_core.runnables.config import RunnableConfig

from ..domain.event import TICK_EVENT_SEQUENCE
from ..graph.state import OverallState
from ..utils.helpers import get_repo

logger = logging.getLogger("aw.svc")


def _build_event(raw: dict) -> dict:
    """把一条原始结果（kind + 扁平字段）转换成 {"type", "payload"} 事件记录 /
    Convert a raw result (kind + flat fields) into a {"type", "payload"} event record."""
    payload = {k: v for k, v in raw.items() if k != "kind"}
    return {"type": raw.get("kind", ""), "payload": payload}


def _dm_create_events(state: OverallState) -> list[dict]:
    """从 dm_service.dm_create 写入的 plot_brief/hints/scene_id 构造 dm_create 原始结果 /
    Build a dm_create raw result from the plot_brief/hints/scene_id written by dm_service.dm_create."""
    scene_id = state.get("scene_id", "")
    if not scene_id:
        return []
    return [
        {
            "kind": "dm_create",
            "scene_id": scene_id,
            "plot_brief": state.get("plot_brief", ""),
            "hints": state.get("hints", []),
        }
    ]


def _scene_events(scene_info: dict[str, Any]) -> list[dict]:
    """从 scene_service 写入的 scene_info 构造 scene_setup 原始结果 /
    Build a scene_setup raw result from the scene_info written by scene_service."""
    scene = scene_info.get("scene") or {}
    scene_id = scene.get("id", "")
    if not scene_id:
        return []
    return [{"kind": "scene_setup", "scene_id": scene_id, "description": "进入场景"}]


def _narrative_events(narrative: str) -> list[dict]:
    """从 dm_service.dm_narrate 写入的 narrative 构造 dm_narrative 原始结果 /
    Build a dm_narrative raw result from the narrative written by dm_service.dm_narrate."""
    if not narrative:
        return []
    return [{"kind": "dm_narrative", "text": narrative}]


def _flatten_pending_actions(pending_actions: list[dict[str, Any]]) -> list[dict]:
    """把 character_service.act 写入的 {order, action_type, target_id, target_type,
    result} 展开成扁平的 kind + 字段原始结果 /
    Flatten the {order, action_type, target_id, target_type, result} shape written
    by character_service.act into a flat kind + fields raw result."""
    flattened = []
    for action in pending_actions:
        result = action.get("result", {}) or {}
        payload = {k: v for k, v in result.items() if k != "kind"}
        payload["order"] = action.get("order")
        payload["target_id"] = action.get("target_id", "")
        payload["target_type"] = action.get("target_type", "")
        flattened.append({"kind": result.get("kind", ""), **payload})
    return flattened


async def flush_events(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 7: 从主图前几个阶段写入 state 的内容（scene_info、pending_actions、
    narrative）构造事件，写入 tick_events 表，再把消息标记为可消费 /
    Build events from the content earlier phases wrote into state (scene_info,
    pending_actions, narrative), persist them to tick_events, then mark the
    message consumable."""
    tick_message_id = state.get("tick_message_id", "")
    if not tick_message_id:
        return {}

    tick = state.get("tick", 0)
    raw_results = [
        *_dm_create_events(state),
        *_scene_events(state.get("scene_info", {})),
        *_flatten_pending_actions(state.get("pending_actions", [])),
        *_narrative_events(state.get("narrative", "")),
    ]
    # 只保留 5 种已知事件类型（dm_create/scene_setup/character_talk/
    # character_interact/dm_narrative），其余（如尚未结算的 character_combat）
    # 不落盘 / Keep only the 5 known event kinds — anything else (e.g. the
    # not-yet-resolved character_combat intent) is dropped here.
    raw_results = [r for r in raw_results if r.get("kind") in TICK_EVENT_SEQUENCE]
    event_repo = get_repo(config, "event")
    if raw_results and event_repo:
        events = [_build_event(raw) for raw in raw_results]
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
