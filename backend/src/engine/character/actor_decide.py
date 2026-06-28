"""Actor Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class ActorDecideInput(TypedDict):
    """Phase 3: 单个 Actor 决策的 Engine 输入"""
    actor_id: str
    plot_brief: str
    tick: int


def actor_decide(input: ActorDecideInput) -> dict[str, Any]:
    """Phase 3: Actor 决策 / Actor decides action. Mock. M5 接入 LLM."""
    return {
        "character_id": input.get("actor_id", ""),
        "type": "idle",
        "description": "Going about daily business.",
    }
