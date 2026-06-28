"""World Service: State ↔ Engine adapter."""
from typing import Any
from ..models.io.world import WorldInput
from ..engine.world.world import execute_instructions
from ..graph.state import OverallState


def world_update(state: OverallState) -> dict[str, Any]:
    """Phase 2: WorldEngine 执行 DM 指令."""
    result = execute_instructions(WorldInput(
        tick=state.get("tick", 0),
        dm_instructions=state.get("dm_instructions", []),
    ))
    return {"world_events": result.events_out}
