"""Event Service: 从 state 构造 TickEvent，不负责持久化."""

from langchain_core.runnables.config import RunnableConfig  # noqa: F401  # type annotation

from ..domain import Action, Decision, PlayerCharacter
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

    scene / scene_objects 来自 state（静态数据），PC/Actor 从领域模型 map 获取最新坐标。
    """
    scene = state.get("scene")
    if scene is None:
        return None
    scene_id = scene.id
    if not scene_id:
        return None
    pcs = [pc.model_dump() for pc in state.get("pcs", {}).values()]
    actors = [actor.model_dump() for actor in state.get("actors", {}).values()]
    scene_objects = state.get("scene_objects", [])
    return TickEvent(
        type=TickEventType.SCENE_SETUP,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "scene": scene.model_dump(),
            "pcs": pcs,
            "actors": actors,
            "scene_objects": [obj.model_dump() for obj in scene_objects],
        },
    )


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
    pcs_map: dict[str, PlayerCharacter] = state.get("pcs", {})
    events: list[TickEvent] = []
    for decision in pc_decisions:
        pc_id = decision.pc_id
        pc_name = getattr(pcs_map.get(pc_id), "name", pc_id)
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
    pcs_map = state.get("pcs", {})
    for action in sorted_actions:
        action_type = action.action_type
        event_type = _EVENT_TYPE_MAP.get(action_type)
        if event_type is None:
            continue
        raw_result = action.result or {}
        # 兼容 Pydantic 模型和 dict / Supports both model and dict
        if isinstance(raw_result, dict):
            result = raw_result
        else:
            result = raw_result.model_dump() if hasattr(raw_result, "model_dump") else {}
        pc_id = action.pc_id
        pc_name = getattr(pcs_map.get(pc_id), "name", pc_id)
        payload = {
            "order": action.order,
            "pc_id": pc_id,
            "pc_name": pc_name,
            "action_type": action_type,
            "target_id": action.target_id,
            "target_type": action.target_type,
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
        if event_type == TickEventType.PC_COMBAT:
            payload["waypoints"] = result.get("waypoints", [])
            payload["narration"] = result.get("narration", "")
            payload["combat_log"] = result.get("combat_log", [])
            payload["winner"] = result.get("winner")
            payload["target_defeated"] = result.get("target_defeated", False)
            payload["result"] = result.get("result", "")
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
    """从 state 各阶段产出统一构造 TickEvent 列表，存入 _pending_events 供 data_service 落盘.

    顺序：dm_create → scene_setup → 每个 PC 的 决策→行动 → ...，保证前端逐 PC 串行展示.
    """
    dm_evts = _pick(_dm_create_event(state), _scene_event(state))
    decisions = _decision_events(state)
    actions = _action_events(state)
    pc_evts = _group_decision_action_pairs(decisions, actions)

    events = [*dm_evts, *pc_evts]
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
