"""DM Service: State ↔ Engine adapter / DM 服务：State ↔ Engine 适配。

职责 / Responsibility:
  - 读取 graph State
  - 构造 Engine 输入 (DMSubState)
  - 调用 Engine 纯函数 (dm_create / dm_narrate)
  - 将结果映射回 graph State key
"""
from typing import Any

from ..engine.dm.dm import DMSubState, dm_create as _dm_create, dm_narrate as _dm_narrate
from ..graph.state import OverallState


def _build_dm_substate(state: OverallState) -> DMSubState:
    """从 graph State 构造 DMSubState / Build DMSubState from graph State."""
    return {
        "tick": state.get("tick", 0),
        "plot_brief": state.get("plot_brief", ""),
        "instructions_out": [],
        "scene_direction": {},
        "narrative_out": "",
        "character_actions": state.get("character_actions", []),
    }


def dm_create(state: OverallState) -> dict[str, Any]:
    """Phase 1: DM 创造情境 / DM creates context.

    graph State → DMSubState → dm_create() → graph State keys.
    产出 / Outputs: dm_instructions, plot_brief, scene_direction
    """
    sub_state = _build_dm_substate(state)
    result = _dm_create(sub_state)
    return {
        "dm_instructions": result.get("instructions_out", []),
        "plot_brief": result.get("plot_brief", ""),
        "scene_direction": result.get("scene_direction", {}),
    }


def dm_narrate(state: OverallState) -> dict[str, Any]:
    """Phase 6: DM 叙事 / DM narrates.

    graph State → DMSubState → dm_narrate() → graph State keys.
    产出 / Outputs: narrative, needs_reflection
    """
    sub_state = _build_dm_substate(state)
    result = _dm_narrate(sub_state)
    return {
        "narrative": result.get("narrative_out", ""),
        "needs_reflection": state.get("tick", 0) % 5 == 0,
    }
