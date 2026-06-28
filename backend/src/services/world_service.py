"""World Service: State ↔ Engine adapter / World 服务：State ↔ Engine 适配。"""
from typing import Any

from ..engine.world.world import WorldEngineSubState, execute_instructions
from ..graph.state import OverallState


def world_update(state: OverallState) -> dict[str, Any]:
    """Phase 2: WorldEngine 执行 DM 指令 / Execute DM instructions.

    graph State → WorldEngineSubState → execute_instructions() → graph State keys.
    产出 / Outputs: world_events
    """
    sub_state: WorldEngineSubState = {
        "tick": state.get("tick", 0),
        "dm_instructions": state.get("dm_instructions", []),
        "events_out": [],
    }
    result = execute_instructions(sub_state)
    return {"world_events": result.get("events_out", [])}
