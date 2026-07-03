"""Quest Service: State ↔ Engine adapter."""

from ..engine.quest import quest_engine
from ..graph.state import EngineSubState
from ..schemas.request import QuestRequest
from ..utils.logging import get_logger


def quest(state: EngineSubState) -> dict:
    get_logger(__name__).info("[quest]")
    """Phase 4: 任务检查."""
    result = quest_engine.check_quests(
        QuestRequest(
            quests=state.get("quests", []),
            event_log=state.get("event_log", []),
        )
    )
    return {"engine_results": [{"engine": "quest", "completed": result.model_dump()}]}
