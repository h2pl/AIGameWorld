"""Actor decision logic / Actor 决策逻辑.

基于 design/04-agent-layer.md §7 / Based on agent layer design.
"""

from typing import TypedDict, Annotated, Any
from operator import add


class ActorSubState(TypedDict):
    """Actor 决策子状态 / Actor decision sub-state."""
    tick: int
    actor_id: str
    plot_brief: str
    character_state: dict[str, Any]
    action: dict[str, Any]


def actor_decide_node(state: ActorSubState) -> dict:
    """Phase 3: Actor 决策 / Actor decides action.

    Mock: 返回预设行动 / Returns preset action.
    后续 M5 接入 LLM / M5 connects to LLM.
    """
    return {
        "action_out": {
            "character_id": state.get("actor_id", "unknown"),
            "type": "idle",
            "description": "Going about daily business.",
        },
    }
