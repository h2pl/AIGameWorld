"""DM Engine: 纯业务逻辑 / Pure business logic (Engine layer).

Engine 层职责: LLM 调用 / Prompt 构造 / 工具协调 / 不依赖 LangGraph
"""

from typing import TypedDict, Any


class DMCreateInput(TypedDict):
    """Phase 1: DM 创造情境的 Engine 输入"""
    tick: int
    plot_brief: str


class DMNarrateInput(TypedDict):
    """Phase 6: DM 叙事的 Engine 输入"""
    tick: int
    plot_brief: str
    dm_instructions: list[dict[str, Any]]
    scene_direction: dict[str, Any]
    character_actions: list[dict[str, Any]]


def dm_create(input: DMCreateInput) -> dict:
    """Phase 1: DM 创造情境 / DM creates context. Mock. M4 接入 LLM."""
    tick = input.get("tick", 0)
    return {
        "instructions_out": [],
        "plot_brief": f"[Tick {tick}] The adventure continues in the Forgotten Realms.",
        "scene_direction": {"featured_pcs": [], "featured_actors": []},
    }


def dm_narrate(input: DMNarrateInput) -> dict:
    """Phase 6: DM 叙事 / DM narrates. Mock. M4 接入 LLM."""
    plot = input.get("plot_brief", "")
    actions = input.get("character_actions", [])
    return {"narrative_out": f"[DM Narrative] {plot} (Actions: {len(actions)})"}
