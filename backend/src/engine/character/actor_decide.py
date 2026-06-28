"""Actor Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class ActorSubState(TypedDict):
    """Actor Service 内部数据契约 / Actor service internal data contract."""
    tick: int
    actor_id: str
    plot_brief: str
    character_state: dict[str, Any]
    action: dict[str, Any]


def actor_decide(actor_id: str, plot_brief: str, tick: int) -> dict[str, Any]:
    """Phase 3: Actor 决策 / Actor decides action. Mock. M5 接入 LLM."""
    return {
        "character_id": actor_id,
        "type": "idle",
        "description": "Going about daily business.",
    }
