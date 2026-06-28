"""DM Service: State ↔ Engine adapter / DM 服务：State ↔ Engine 适配。"""
from typing import Any

from ..models.dm import DMCreateInput, DMNarrateInput
from ..engine.dm.dm import dm_create as _dm_create, dm_narrate as _dm_narrate
from ..graph.state import OverallState


def _to_dm_create_input(state: OverallState) -> DMCreateInput:
    """① State → Engine 输入"""
    return {"tick": state.get("tick", 0), "plot_brief": state.get("plot_brief", "")}


def _to_dm_narrate_input(state: OverallState) -> DMNarrateInput:
    """① State → Engine 输入"""
    return {
        "tick": state.get("tick", 0),
        "plot_brief": state.get("plot_brief", ""),
        "dm_instructions": state.get("dm_instructions", []),
        "scene_direction": state.get("scene_direction", {}),
        "character_actions": state.get("character_actions", []),
    }


def dm_create(state: OverallState) -> dict[str, Any]:
    """Phase 1: DM 创造情境 / DM creates context.

    ① State → DMCreateInput  ② 调用 Engine  ③ 映射回 State key
    产出 / Outputs: dm_instructions, plot_brief, scene_direction
    """
    engine_input = _to_dm_create_input(state)
    result = _dm_create(engine_input)
    return {
        "dm_instructions": result.get("instructions_out", []),
        "plot_brief": result.get("plot_brief", ""),
        "scene_direction": result.get("scene_direction", {}),
    }


def dm_narrate(state: OverallState) -> dict[str, Any]:
    """Phase 6: DM 叙事 / DM narrates.

    ① State → DMNarrateInput  ② 调用 Engine  ③ 映射回 State key
    产出 / Outputs: narrative, needs_reflection
    """
    engine_input = _to_dm_narrate_input(state)
    result = _dm_narrate(engine_input)
    return {
        "narrative": result.get("narrative_out", ""),
        "needs_reflection": state.get("tick", 0) % 5 == 0,
    }
