"""Quest Service: State ↔ Engine adapter."""
from typing import Any
from ..schemas.request import QuestRequest
from ..engine.quest.quest import check_quests as _check_quests
from ..graph.state import EngineSubState


def quest(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 任务检查."""
    result = _check_quests(QuestRequest(
        quests=state.get("quests", []),
        event_log=state.get("event_log", []),
    ))
    return {"engine_results": [{"engine": "quest", "completed": result.model_dump()}]}
