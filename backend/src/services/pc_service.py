"""PC Service: 决策 + 执行编排 / PC decide + act orchestration（坐标更新下沉到 engine）"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import Action, Decision
from ..engine.combat import combat_engine
from ..engine.decision import decision_engine
from ..engine.explore import explore_engine
from ..engine.interact import interact_engine
from ..engine.talk import talk_engine
from ..graph.state import OverallState
from ..utils.logging import trace_node


@trace_node("pc.decide")
async def decide(state: OverallState, config: RunnableConfig = None) -> dict:
    """为场景内每个 PC 决策。PC 列表从 pcs map 获取（实时），不从 scene 读."""
    pcs = state.get("pcs", {})
    if not pcs:
        return {"pc_decisions": []}

    # 从 state 读取领域模型 / Read domain models from state
    dm_record = state.get("dm_record")
    scene = state.get("scene")
    scene_objects = state.get("scene_objects", [])
    actors = state.get("actors", {})
    tick = state.get("tick", 0)
    decisions: list[Decision] = []
    # 逐个 PC 调用决策引擎 / Delegate each PC to decision engine
    for pc_id in pcs:
        decision = await decision_engine.decide(
            pc_id=pc_id,
            tick=tick,
            scene=scene,
            scene_objects=scene_objects,
            pcs=pcs,
            actors=actors,
            dm_record=dm_record,
            config=config,
        )
        if decision:
            decisions.append(decision)
    return {"pc_decisions": decisions}


@trace_node("pc.act")
async def act(state: OverallState, config: RunnableConfig = None) -> dict:
    """执行 PC 决策（坐标更新下沉到各 engine）"""
    decisions = state.get("pc_decisions", [])
    if not decisions:
        return {}

    # 从 state 读取领域模型 / Read domain models from state
    tick = state.get("tick", 0)
    dm_record = state.get("dm_record")
    scene = state.get("scene")
    scene_objects = state.get("scene_objects", [])
    pcs = state.get("pcs", {})
    actors = state.get("actors", {})
    memories = state.get("memories", {})
    actions: list[Action] = []

    # 逐个决策分发到对应 action engine / Dispatch each decision to matching action engine
    for order, decision in enumerate(decisions):
        # 各 engine 内部自行更新 pcs 坐标
        talk_action = await talk_engine.process_talk_action(
            decision=decision,
            tick=tick,
            scene=scene,
            scene_objects=scene_objects,
            pcs=pcs,
            actors=actors,
            dm_record=dm_record,
            memories=memories,
            config=config,
        )
        interact_action = await interact_engine.process_interact_action(
            decision=decision,
            tick=tick,
            scene=scene,
            scene_objects=scene_objects,
            pcs=pcs,
            actors=actors,
            dm_record=dm_record,
            memories=memories,
            config=config,
        )
        combat_action = await combat_engine.process_combat_action(
            decision=decision,
            tick=tick,
            scene=scene,
            scene_objects=scene_objects,
            pcs=pcs,
            actors=actors,
            dm_record=dm_record,
            memories=memories,
            config=config,
        )
        explore_action = await explore_engine.process_explore_action(
            decision=decision,
            tick=tick,
            scene=scene,
            scene_objects=scene_objects,
            pcs=pcs,
            actors=actors,
            dm_record=dm_record,
            memories=memories,
            config=config,
        )

        # 一个 decision 只对应一个 effective action / One decision → one effective action
        action = talk_action or interact_action or combat_action or explore_action
        if action is None:
            continue

        # 设置 action 执行顺序 / Set action execution order
        action.order = order
        actions.append(action)

    # 组装返回 state 更新 / Assemble state update
    result: dict = {"actions": actions}
    # engine 已直接修改 pcs 和 memories，回写 state / Engines mutated pcs/memories in place, write back
    if pcs:
        result["pcs"] = pcs
    if memories:
        result["memories"] = memories
    return result
