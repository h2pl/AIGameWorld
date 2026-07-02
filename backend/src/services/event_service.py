"""Event Service: State ↔ Repo adapter——统一构造 + 落盘事件.

其他 service/engine 只把原始结果（带 "kind" 字段的 dict）放进
state["pending_events"]，不构造事件、也不直接碰 event_repo；本服务是
主图最后一步，唯一负责把这些原始结果转换成 {"type", "payload"} 事件记录并
批量写入 tick_events 表 /
Other services/engines only append raw results (dicts tagged with a "kind"
field) to state["pending_events"] — they never build event records or touch
event_repo directly. This service is the last step of the main tick graph
and the sole place that turns those raw results into {"type", "payload"}
event records and flushes them to the tick_events table.
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ..graph.state import OverallState
from ..utils.helpers import get_repo

logger = logging.getLogger("aw.svc")


def _build_event(raw: dict) -> dict:
    """把一条原始结果（kind + 扁平字段）转换成 {"type", "payload"} 事件记录 /
    Convert a raw result (kind + flat fields) into a {"type", "payload"} event record."""
    payload = {k: v for k, v in raw.items() if k != "kind"}
    return {"type": raw.get("kind", ""), "payload": payload}


async def flush_events(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 7: 用 state 中累积的原始结果构造事件，一次性写入 tick_events 表."""
    raw_results = state.get("pending_events", [])
    tick_message_id = state.get("tick_message_id", "")
    if not raw_results or not tick_message_id:
        return {}

    event_repo = get_repo(config, "event")
    if not event_repo:
        return {}

    events = [_build_event(raw) for raw in raw_results]
    tick = state.get("tick", 0)
    await event_repo.insert_tick_events(tick_message_id, tick, events)
    logger.info(
        "[event] flushed tick=%s tick_message_id=%s count=%d", tick, tick_message_id, len(events)
    )
    return {}
