"""Character Service: State ↔ Engine adapter——角色决策.

场景信息由 scene_service.build_scene_info 提前构建好并注入 state（与谁来用无关，
不区分 PC），这里直接消费 state["scene_info"]，为场景内每个 PC 逐个决策 /
Scene info is built and injected into state upfront by
scene_service.build_scene_info (consumer-independent, not per-PC); this module
just consumes state["scene_info"] and decides for each PC in the scene.
"""

from langchain_core.runnables.config import RunnableConfig

from ..engine.combat import combat_engine
from ..engine.decision import decision_engine
from ..engine.explore import explore_engine
from ..engine.interact import interact_engine
from ..engine.talk import talk_engine
from ..graph.state import OverallState
from ..utils.logging import trace_node


@trace_node("pc.decide")
async def decide(state: OverallState, config: RunnableConfig = None) -> dict:
    """基于场景信息为场景内每个 PC 决策 / Decide for each PC in the scene, based on the scene info."""
    scene_info = state.get("scene_info", {})
    pcs = scene_info.get("pcs", [])
    if not pcs:
        return {"pc_decisions": []}

    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    scene_id = state.get("scene_id", "")
    decisions: list[dict] = []
    for pc in pcs:
        decision = await decision_engine.decide(
            pc_id=pc.get("id", ""),
            scene_info=scene_info,
            plot_brief=plot_brief,
            hints=hints,
            scene_id=scene_id,
            tick=state.get("tick", 0),
            config=config,
        )
        if decision:
            decisions.append(decision)

    return {"pc_decisions": decisions}


@trace_node("pc.act")
async def act(state: OverallState, config: RunnableConfig = None) -> dict:
    """执行角色决策，把各 engine 产生的原始结果统一格式化成
    {order, action_type, target_id, target_type, result} 交给 event_service /
    Execute pc decisions, formatting each engine's raw result into a
    uniform {order, action_type, target_id, target_type, result} dict for
    event_service."""
    decisions = state.get("pc_decisions", [])
    if not decisions:
        return {}

    tick = state.get("tick", 0)
    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    scene_id = state.get("scene_id", "")
    scene_info = state.get("scene_info", {})
    pc_state_map = state.get("pc_state_map", {})
    pending_actions: list[dict] = []
    for order, decision in enumerate(decisions):
        talk_result = await talk_engine.process_talk_action(
            decision=decision,
            plot_brief=plot_brief,
            hints=hints,
            scene_id=scene_id,
            tick=tick,
            config=config,
        )
        interact_result = await interact_engine.process_interact_action(
            decision=decision,
            config=config,
        )
        # combat 目前只记录意图，完整结算见 combat_engine.py 顶部 TODO
        # combat only records intent for now, see TODO atop combat_engine.py
        combat_result = await combat_engine.process_combat_action(
            decision=decision,
            config=config,
        )
        explore_result = explore_engine.process_explore_action(
            decision=decision,
            scene_info=scene_info,
            pc_state_map=pc_state_map,
        )
        result = talk_result or interact_result or combat_result or explore_result
        if result is None:
            continue
        pending_actions.append(
            {
                "order": order,
                "pc_id": decision.get("pc_id", ""),
                "action_type": decision.get("type", ""),
                "target_id": decision.get("target_id", ""),
                "target_type": decision.get("target_type", ""),
                "result": result,
            }
        )
    return {"pending_actions": pending_actions}
