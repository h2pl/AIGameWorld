"""World Service: State ↔ Engine adapter / World 服务：State ↔ Engine 适配。"""
from typing import Any

from ..engine.world.world import WorldInput, execute_instructions
from ..graph.state import OverallState


def _to_world_input(state: OverallState) -> WorldInput:
    """① State → Engine 输入"""
    return {
        "tick": state.get("tick", 0),
        "dm_instructions": state.get("dm_instructions", []),
    }


def world_update(state: OverallState) -> dict[str, Any]:
    """Phase 2: WorldEngine 执行 DM 指令 / Execute DM instructions.

    ① State → WorldInput
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: world_events
    """
    engine_input = _to_world_input(state)                            # ①
    result = execute_instructions(engine_input)                      # ②
    return {"world_events": result.get("events_out", [])}            # ③
