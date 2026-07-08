"""Quest Service: State ↔ Engine adapter."""

from ..engine.quest import quest_engine
from ..graph.state import EngineSubState
from ..utils.logging import get_logger


def quest(state: EngineSubState) -> dict:
    get_logger(__name__).info("[service]")
    """Phase 4: 任务检查."""
    result = quest_engine.check_quests(
        quests=state.get("quests", []),
    )
    return {"engine_results": [{"engine": "quest", "completed": result}]}
