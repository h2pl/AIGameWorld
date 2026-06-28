"""PC Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class PCDecideInput(TypedDict):
    """Phase 3: 单个 PC 决策的 Engine 输入"""
    pc_id: str
    plot_brief: str
    tick: int


def pc_decide(input: PCDecideInput) -> dict[str, Any]:
    """Phase 3: PC 决策 / PC decides action. Mock. M5 接入 LLM."""
    return {
        "character_id": input.get("pc_id", ""),
        "type": "explore",
        "description": "Looking around the area.",
    }
