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


def _to_dm_input(state: OverallState) -> DMSubState:
    """① State → Engine 输入"""
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

    ① State → DMSubState
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: dm_instructions, plot_brief, scene_direction
    """
    engine_input = _to_dm_input(state)                              # ①
    result = _dm_create(engine_input)                               # ②
    return {                                                        # ③
        "dm_instructions": result.get("instructions_out", []),
        "plot_brief": result.get("plot_brief", ""),
        "scene_direction": result.get("scene_direction", {}),
    }


def dm_narrate(state: OverallState) -> dict[str, Any]:
    """Phase 6: DM 叙事 / DM narrates.

    ① State → DMSubState
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: narrative, needs_reflection
    """
    engine_input = _to_dm_input(state)                              # ①
    result = _dm_narrate(engine_input)                              # ②
    return {                                                        # ③
        "narrative": result.get("narrative_out", ""),
        "needs_reflection": state.get("tick", 0) % 5 == 0,
    }
