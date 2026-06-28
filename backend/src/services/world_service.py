"""World Service: State ↔ Engine adapter."""
from typing import Any
from ..models.world import WorldInput
from ..engine.world.world import execute_instructions
from ..graph.state import OverallState


def _to_world_input(state: OverallState) -> WorldInput:
    """① State → Engine 输入"""
    return {"tick": state.get("tick", 0), "dm_instructions": state.get("dm_instructions", [])}


def world_update(state: OverallState) -> dict[str, Any]:
    """Phase 2: WorldEngine 执行 DM 指令. 产出 / Outputs: world_events"""
    engine_input = _to_world_input(state)
    result = execute_instructions(engine_input)
    return {"world_events": result.get("events_out", [])}
