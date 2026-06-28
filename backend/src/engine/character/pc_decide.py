"""PC Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class PCSubState(TypedDict):
    """PC Service 内部数据契约 / PC service internal data contract."""
    tick: int
    pc_id: str
    plot_brief: str
    character_state: dict[str, Any]
    action: dict[str, Any]


def pc_decide(pc_id: str, plot_brief: str, tick: int) -> dict[str, Any]:
    """Phase 3: PC 决策 / PC decides action. Mock. M5 接入 LLM."""
    return {
        "character_id": pc_id,
        "type": "explore",
        "description": "Looking around the area.",
    }
