"""DM Service: 纯业务逻辑 / Pure business logic (Service layer).

Service 层职责: 封装业务逻辑 / LLM 调用 / Prompt 构造 / 工具协调 / 不依赖 LangGraph
"""

from typing import TypedDict, Any


class DMSubState(TypedDict):
    """DM Service 内部数据契约 / DM service internal data contract."""
    tick: int
    plot_brief: str
    instructions_out: list[dict[str, Any]]
    scene_direction: dict[str, Any]
    narrative_out: str
    character_actions: list[dict[str, Any]]


def dm_create(state: DMSubState) -> dict:
    """Phase 1: DM 创造情境 / DM creates context. Mock. M4 接入 LLM."""
    tick = state.get("tick", 0)
    return {
        "plot_brief": f"[Tick {tick}] The adventure continues in the Forgotten Realms.",
        "instructions_out": [],
        "scene_direction": {"featured_pcs": [], "featured_actors": []},
    }


def dm_narrate(state: DMSubState) -> dict:
    """Phase 6: DM 叙事 / DM narrates. Mock. M4 接入 LLM."""
    plot = state.get("plot_brief", "")
    actions = state.get("character_actions", [])
    narrative = f"[DM Narrative] {plot} (Actions: {len(actions)})"
    return {"narrative_out": narrative}
