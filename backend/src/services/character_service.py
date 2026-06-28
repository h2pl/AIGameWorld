"""Character Service: PC + Actor decision adapter / 角色服务：PC + Actor 决策适配。"""
from typing import Any
from ..engine.character.pc_decide import PCDecideInput, pc_decide as _pc_decide
from ..engine.character.actor_decide import ActorDecideInput, actor_decide as _actor_decide
from ..graph.state import CharacterSubState


def _to_pc_input(state: CharacterSubState, pc_id: str) -> PCDecideInput:
    """① State → Engine 输入（per-PC）"""
    return {
        "pc_id": pc_id,
        "plot_brief": state.get("plot_brief", ""),
        "tick": state.get("tick", 0),
    }


def _to_actor_input(state: CharacterSubState, actor_id: str) -> ActorDecideInput:
    """① State → Engine 输入（per-Actor）"""
    return {
        "actor_id": actor_id,
        "plot_brief": state.get("plot_brief", ""),
        "tick": state.get("tick", 0),
    }


def pc_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured PC 决策 / All featured PCs decide.

    ① 遍历 scene_direction.featured_pcs → PCDecideInput
    ② 调用 Engine per-PC
    ③ 汇总为 character_actions
    产出 / Outputs: character_actions (add reducer)
    """
    direction = state.get("scene_direction", {})
    actions = []
    for pc_id in direction.get("featured_pcs", []):
        engine_input = _to_pc_input(state, pc_id)                   # ①
        action = _pc_decide(engine_input)                           # ②
        if action:
            actions.append(action)
    return {"character_actions": actions}                            # ③


def actor_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured Actor 决策 / All featured Actors decide.

    ① 遍历 scene_direction.featured_actors → ActorDecideInput
    ② 调用 Engine per-Actor
    ③ 汇总为 character_actions
    产出 / Outputs: character_actions (add reducer)
    """
    direction = state.get("scene_direction", {})
    actions = []
    for actor_id in direction.get("featured_actors", []):
        engine_input = _to_actor_input(state, actor_id)             # ①
        action = _actor_decide(engine_input)                        # ②
        if action:
            actions.append(action)
    return {"character_actions": actions}                            # ③
