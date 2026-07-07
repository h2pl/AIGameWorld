"""PC Service: 决策 + 执行编排 / PC decide + act orchestration（坐标更新下沉到 engine）"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import Action, Decision, Scene, SceneObject
from ..engine.combat import combat_engine
from ..engine.decision import decision_engine
from ..engine.explore import explore_engine
from ..engine.interact import interact_engine
from ..engine.talk import talk_engine
from ..graph.state import OverallState
from ..utils.logging import trace_node


def _as_scene_dict(scene: Scene | None) -> dict:
    """把 Scene 领域模型转成 engine 可读的 dict（engine 内部仍按 dict 处理）."""
    if scene is None:
        return {}
    return scene.model_dump()


def _as_object_dicts(scene_objects: list[SceneObject]) -> list[dict]:
    """把 SceneObject 列表转成 dict 列表."""
    return [obj.model_dump() for obj in scene_objects]


@trace_node("pc.decide")
async def decide(state: OverallState, config: RunnableConfig = None) -> dict:
    """为场景内每个 PC 决策。PC 列表从 pcs map 获取（实时），不从 scene 读."""
    pcs = state.get("pcs", {})
    if not pcs:
        return {"pc_decisions": []}

    scene = state.get("scene")
    scene_objects = state.get("scene_objects", [])
    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    scene_id = state.get("scene_id", "")
    actors = state.get("actors", {})
    tick = state.get("tick", 0)
    decisions: list[Decision] = []
    for pc_id in pcs:
        decision = await decision_engine.decide(
            pc_id=pc_id,
            scene=scene,
            plot_brief=plot_brief,
            hints=hints,
            scene_id=scene_id,
            tick=tick,
            pcs=pcs,
            actors=actors,
            scene_objects=scene_objects,
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

    tick = state.get("tick", 0)
    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    scene_id = state.get("scene_id", "")
    scene = state.get("scene")
    scene_objects = state.get("scene_objects", [])
    scene_dict = _as_scene_dict(scene)
    object_dicts = _as_object_dicts(scene_objects)
    pcs = state.get("pcs", {})
    actors = state.get("actors", {})
    pc_memory_map = state.get("pc_memory_map", {})
    actions: list[Action] = []

    for order, decision in enumerate(decisions):
        pc_id = decision.pc_id
        target_id = decision.target_id or ""
        decision_dict = decision.model_dump()

        # 各 engine 内部自行更新 pcs 坐标
        talk_result = await talk_engine.process_talk_action(
            decision=decision_dict,
            plot_brief=plot_brief,
            hints=hints,
            scene_id=scene_id,
            tick=tick,
            pcs=pcs,
            actors=actors,
            pc_memory_map=pc_memory_map,
            config=config,
        )
        interact_result = await interact_engine.process_interact_action(
            decision=decision_dict,
            scene=scene_dict,
            scene_objects=object_dicts,
            pcs=pcs,
            actors=actors,
            tick=tick,
            plot_brief=plot_brief,
            hints=hints,
            pc_memory_map=pc_memory_map,
            config=config,
        )
        combat_result = await combat_engine.process_combat_action(
            decision=decision_dict,
            scene=scene_dict,
            pcs=pcs,
            actors=actors,
            plot_brief=plot_brief,
            hints=hints,
            tick=tick,
            pc_memory_map=pc_memory_map,
            config=config,
        )
        explore_result = await explore_engine.process_explore_action(
            decision=decision_dict,
            scene=scene_dict,
            scene_objects=object_dicts,
            pcs=pcs,
            actors=actors,
            plot_brief=plot_brief,
            hints=hints,
            tick=tick,
            pc_memory_map=pc_memory_map,
            config=config,
        )

        # 一个 decision 只对应一个 effective action / One decision → one effective action
        action_result = talk_result or interact_result or combat_result or explore_result
        if action_result is None:
            continue

        actions.append(
            Action(
                order=order,
                pc_id=pc_id,
                action_type=decision.type,
                target_id=target_id,
                target_type=decision.target_type or "",
                result=action_result,
            )
        )

    result: dict = {"actions": actions}
    if pcs:
        result["pcs"] = pcs
    if pc_memory_map:
        result["pc_memory_map"] = pc_memory_map
    return result
