"""PC Service: 决策 + 执行编排 / PC decide + act orchestration（坐标更新下沉到 engine）"""

# 每个 tick 内逐个 action 执行，engine 自行维护 pc_state_map
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
    """为场景内每个 PC 决策。PC 列表从 pc_state_map 获取（实时），不从 scene_info["pcs"] 读."""
    pc_state_map = state.get("pc_state_map", {})
    if not pc_state_map:
        return {"pc_decisions": []}

    scene_info = state.get("scene_info", {})
    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    scene_id = state.get("scene_id", "")
    actor_state_map = state.get("actor_state_map", {})
    tick = state.get("tick", 0)
    decisions: list[dict] = []
    for pc_id in pc_state_map:
        pc_decisions = await decision_engine.decide(
            pc_id=pc_id,
            scene_info=scene_info,
            plot_brief=plot_brief,
            hints=hints,
            scene_id=scene_id,
            tick=tick,
            pc_state_map=pc_state_map,
            actor_state_map=actor_state_map,
            config=config,
        )
        decisions.extend(pc_decisions)
    return {"pc_decisions": decisions}


@trace_node("pc.act")
async def act(state: OverallState, config: RunnableConfig = None) -> dict:
    """执行 PC 决策（坐标更新下沉到各 engine）"""
    decisions = state.get("pc_decisions", [])
    if not decisions:
        return {}

    tick = state.get("tick", 0)
    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    scene_id = state.get("scene_id", "")
    scene_info = state.get("scene_info", {})
    pc_state_map = state.get("pc_state_map", {})
    actor_state_map = state.get("actor_state_map", {})
    pending_actions: list[dict] = []

    for order, decision in enumerate(decisions):
        pc_id = decision.get("pc_id", "")
        target_id = decision.get("target_id", "")

        # 各 engine 内部自行更新 pc_state_map 坐标
        talk_result = await talk_engine.process_talk_action(
            decision=decision,
            plot_brief=plot_brief,
            hints=hints,
            scene_id=scene_id,
            tick=tick,
            pc_state_map=pc_state_map,
            actor_state_map=actor_state_map,
            config=config,
        )
        interact_result = await interact_engine.process_interact_action(
            decision=decision,
            scene_info=scene_info,
            pc_state_map=pc_state_map,
            actor_state_map=actor_state_map,
            tick=tick,
            plot_brief=plot_brief,
            hints=hints,
            config=config,
        )
        combat_result = await combat_engine.process_combat_action(decision=decision, config=config)
        explore_result = await explore_engine.process_explore_action(
            decision=decision,
            scene_info=scene_info,
            pc_state_map=pc_state_map,
            actor_state_map=actor_state_map,
            plot_brief=plot_brief,
            hints=hints,
            tick=tick,
            config=config,
        )

        # 一个 decision 只对应一个 effective action / One decision → one effective action
        result = talk_result or interact_result or combat_result or explore_result
        if result is None:
            continue

        pending_actions.append(
            {
                "order": order,  # 执行顺序 / Execution order
                "pc_id": pc_id,  # 执行者 / Executor
                "action_type": decision.get("type", ""),  # talk/interact/combat/explore
                "target_id": target_id,  # 目标 / Target
                "target_type": decision.get("target_type", ""),  # pc/actor/scene_object
                "result": result,  # engine 返回模型 / Engine result model
            }
        )

    result = {"pending_actions": pending_actions}
    if pc_state_map:
        result["pc_state_map"] = pc_state_map
    return result
