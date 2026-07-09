"""Event Service: 从 state 构造 TickEvent，不负责持久化."""

from langchain_core.runnables.config import RunnableConfig  # noqa: F401  # type annotation

from ..domain import Action, Decision, PlayerCharacter
from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..utils.logging import get_logger

logger = get_logger(__name__)


_EVENT_TYPE_MAP: dict[str, TickEventType] = {
    "talk": TickEventType.PC_TALK,
    "interact": TickEventType.PC_INTERACT,
    "explore": TickEventType.PC_EXPLORE,
    "combat": TickEventType.PC_COMBAT,
}


def _decision_events(state: OverallState) -> list[TickEvent]:
    """从 pc_decisions 构造 pc_decision 事件（思考+决策），在动作执行前展示."""
    pc_decisions: list[Decision] = state.get("pc_decisions", [])
    if not pc_decisions:
        return []
    tick = state.get("tick", 0)
    pcs: dict[str, PlayerCharacter] = state.get("pcs", {})
    events: list[TickEvent] = []
    for decision in pc_decisions:
        pc_id = decision.pc_id
        pc_name = getattr(pcs.get(pc_id), "name", pc_id)
        action_type = decision.type or "wait"
        payload: dict = {
            "pc_id": pc_id,
            "pc_name": pc_name,
            "action_type": action_type,
            "target_id": decision.target_id or "",
            "target_type": decision.target_type or "",
            "thought": decision.thought,
        }
        # explore 时传递探索目标坐标 / pass explore target coordinates
        if action_type == "explore":
            if decision.explore_x is not None:
                payload["explore_x"] = decision.explore_x
            if decision.explore_y is not None:
                payload["explore_y"] = decision.explore_y
        events.append(
            TickEvent(
                type=TickEventType.PC_DECISION,
                tick=tick,
                world_id=state.get("world_id", ""),
                payload=payload,
            )
        )
    return events


def _action_events(state: OverallState) -> list[TickEvent]:
    """从 actions 构造 character_talk / character_explore 等事件."""
    actions: list[Action] = state.get("actions", [])
    if not actions:
        return []
    tick = state.get("tick", 0)
    sorted_actions = sorted(actions, key=lambda a: a.order)
    events: list[TickEvent] = []
    pcs: dict[str, PlayerCharacter] = state.get("pcs", {})
    for action in sorted_actions:
        action_type = action.action_type
        event_type = _EVENT_TYPE_MAP.get(action_type)
        if event_type is None:
            continue
        pc_id = action.pc_id
        pc_name = getattr(pcs.get(pc_id), "name", pc_id)
        payload = {
            "order": action.order,
            "pc_id": pc_id,
            "pc_name": pc_name,
            "action_type": action_type,
            "target_id": action.target_id,
            "target_type": action.target_type,
        }
        if event_type == TickEventType.PC_TALK:
            payload["waypoints"] = action.waypoints
            payload["turns"] = action.turns
            payload["participants"] = action.participants
        if event_type == TickEventType.PC_EXPLORE:
            payload["waypoints"] = action.waypoints
            payload["explore_record"] = action.explore_record
        if event_type == TickEventType.PC_INTERACT:
            payload["waypoints"] = action.waypoints
            payload["narration"] = action.narration
            payload["success"] = action.success
            payload["object_id"] = action.object_id
        if event_type == TickEventType.PC_COMBAT:
            payload["waypoints"] = action.waypoints
            payload["narration"] = action.narration
            payload["combat_log"] = action.combat_log
            payload["winner"] = action.winner
            payload["target_defeated"] = action.target_defeated
            payload["result"] = action.result
        events.append(
            TickEvent(
                type=event_type,
                tick=tick,
                world_id=state.get("world_id", ""),
                payload=payload,
            )
        )
    return events


def _group_decision_action_pairs(
    decisions: list[TickEvent],
    actions: list[TickEvent],
) -> list[TickEvent]:
    """按 PC 交织决策和行动事件：每个 PC 的 决策→行动 依次排列."""
    # 构建 pc_id → action_event 映射 / Build pc_id → action_event map
    action_map: dict[str, TickEvent] = {}
    unmatched: list[TickEvent] = []
    for a in actions:
        pc_id = a.payload.get("pc_id", "")
        if pc_id:
            action_map[pc_id] = a
        else:
            unmatched.append(a)

    paired: list[TickEvent] = []
    for d in decisions:
        pc_id = d.payload.get("pc_id", "")
        paired.append(d)  # 先放决策 / decision first
        action = action_map.pop(pc_id, None)
        if action:
            paired.append(action)  # 再放行动 / action after
    # 兜底：未匹配到 decision 的 action 放末尾 / unmatched actions at end
    paired.extend(action_map.values())
    paired.extend(unmatched)

    return paired


def flush_events(state: OverallState, config: RunnableConfig = None) -> dict:
    """从 tick_init 快照构建 scene_setup，追加 PC 决策/行动事件"""
    decisions = _decision_events(state)
    actions = _action_events(state)
    pc_evts = _group_decision_action_pairs(decisions, actions)

    prev_events = list(state.get("tick_events", []))

    # 用 pcs_snapshot 构建 scene_setup / Build scene_setup from snapshot
    snapshot = state.get("pcs_snapshot", {})
    ss = _scene_setup_from_snapshot(state, snapshot)
    if ss:
        prev_events = [ss, *prev_events]

    events = [*prev_events, *pc_evts]
    tick = state.get("tick", 0)
    logger.info("[service] flushed events tick=%s count=%d", tick, len(events))
    return {"tick_events": events}


def _scene_setup_from_snapshot(state: OverallState, snapshot: dict) -> TickEvent | None:
    """从 pcs_snapshot 构建 scene_setup TickEvent"""
    scene_data = snapshot.get("scene")
    if not scene_data:
        return None
    scene_id = scene_data.get("id", "")
    if not scene_id:
        return None
    return TickEvent(
        type=TickEventType.SCENE_SETUP,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "scene": scene_data,
            "pcs": list(snapshot.get("pcs", {}).values()),
            "actors": list(snapshot.get("actors", {}).values()),
            "scene_objects": snapshot.get("scene_objects", []),
        },
    )


def emit_narrative_event(state: OverallState, config: RunnableConfig = None) -> dict:
    """将 dm_record.dm_narrative 转为 DM_NARRATIVE 事件追加到 tick_events."""
    dm = state.get("dm_record")
    narrative = dm.dm_narrative if dm else ""
    events = list(state.get("tick_events", []))
    if narrative:
        events.append(
            TickEvent(
                type=TickEventType.DM_NARRATIVE,
                tick=state.get("tick", 0),
                world_id=state.get("world_id", ""),
                payload={"text": narrative},
            )
        )
    return {"tick_events": events}
