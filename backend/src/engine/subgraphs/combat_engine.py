"""CombatEngine 子图 / Combat Engine Subgraph.
Phase 4: 回合制战斗（独立 tick 子循环）/ Turn-based combat (independent tick sub-loop).
Mock: 返回空结果. 后续 M6 接入 / Mock: empty result. M6 integration.
"""

from typing import TypedDict, Any


class CombatSubState(TypedDict):
    """CombatEngine 子图状态 / CombatEngine subgraph state."""
    participants: list[str]  # 参战者 ID 列表 / Participant IDs
    initiative_order: list[tuple[str, int]]  # 先攻顺序 / Initiative order
    round: int  # 当前轮次 / Current round
    actions: list[dict[str, Any]]  # 战斗动作 / Combat actions
    combat_log: list[str]  # 战斗日志 / Combat log
    result: dict[str, Any]  # 战斗结果 / Combat result


def resolve_combat(state: dict[str, Any]) -> CombatSubState:
    """解析战斗 / Resolve combat.
    
    Mock: 空战斗结果.
    """
    return CombatSubState(
        participants=state.get("participants", []),
        initiative_order=state.get("initiative_order", []),
        round=state.get("round", 1),
        actions=[],
        combat_log=[],
        result={"victory": None, "casualties": [], "loot": []},
    )
