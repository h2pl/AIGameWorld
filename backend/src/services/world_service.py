"""World Service: State ↔ Engine adapter."""
import logging

from ..engine.world import world as world_engine
from ..graph.state import OverallState
from ..schemas.request import WorldUpdateRequest


def world_update(state: OverallState) -> dict:
    logging.getLogger("aw.svc").info("[world]")
    """Phase 2: WorldEngine 执行 DM 指令."""
    result = world_engine.execute_instructions(
        WorldUpdateRequest(
            tick=state.get("tick", 0),
            dm_instructions=state.get("dm_instructions", []),
        )
    )
    return {"world_events": result.events_out}
