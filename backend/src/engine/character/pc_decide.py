"""PC decision logic / PC 决策逻辑.

基于 design/04-agent-layer.md §6 / Based on agent layer design.
"""

from typing import TypedDict, Annotated, Any
from operator import add


class PCSubState(TypedDict):
    """PC 决策子状态 / PC decision sub-state."""
    tick: int
    pc_id: str
    plot_brief: str
    character_state: dict[str, Any]
    action: dict[str, Any]


def pc_decide_node(state: PCSubState) -> dict:
    """Phase 3: PC 决策 / PC decides action.

    Mock: 返回预设行动 / Returns preset action.
    后续 M5 接入 LLM / M5 connects to LLM.
    """
    return {
        "action_out": {
            "character_id": state.get("pc_id", "unknown"),
            "type": "explore",
            "description": "Looking around the area.",
        },
    }
