"""ExplorationEngine 子图 / Exploration Engine Subgraph.
Phase 4: 移动/交互 DC 检定 / Movement/interaction DC check.
Mock: 返回空结果. 后续 M7 接入 / Mock: empty result. M7 integration.
"""

from typing import TypedDict, Any


class ExplorationSubState(TypedDict):
    """ExplorationEngine 子图状态 / ExplorationEngine subgraph state."""
    character_id: str  # 角色 ID / Character ID
    action_type: str  # move/interact/search / Action type
    target: str  # 目标 ID / Target ID
    check_result: dict[str, Any]  # 检定结果 / Check result


def resolve_exploration(state: dict[str, Any]) -> ExplorationSubState:
    """解析探索检定 / Resolve exploration check.
    
    Mock: 空检定结果.
    """
    return ExplorationSubState(
        character_id=state.get("character_id", ""),
        action_type=state.get("action_type", "move"),
        target=state.get("target", ""),
        check_result={},
    )
