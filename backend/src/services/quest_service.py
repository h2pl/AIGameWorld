"""Quest Service: State ↔ Engine adapter."""
from typing import Any
from ..models.engine import QuestInput
from ..engine.quest.quest import check_quests as _check_quests
from ..graph.state import EngineSubState


def _to_quest_input(state: EngineSubState) -> QuestInput:
    return {"quests": state.get("quests", []), "event_log": state.get("event_log", [])}


def quest(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 任务检查. 产出 / Outputs: engine_results"""
    completed = _check_quests(_to_quest_input(state))
    return {"engine_results": [{"engine": "quest", "completed": completed}]}
