"""Quest Service: State ↔ Engine adapter."""
from typing import Any
from ..models.io.engine import QuestInput
from ..engine.quest.quest import check_quests as _check_quests
from ..graph.state import EngineSubState


def quest(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 任务检查."""
    completed = _check_quests(QuestInput(
        quests=state.get("quests", []),
        event_log=state.get("event_log", []),
    ))
    return {"engine_results": [{"engine": "quest", "completed": completed}]}
