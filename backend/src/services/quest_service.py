"""Quest Service: State ↔ Engine adapter / 任务服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.quest.quest import check_quests as _check_quests
from ..graph.state import EngineSubState


def quest(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 任务检查 / Quest completion check.

    产出 / Outputs: engine_results
    """
    completed = _check_quests(
        quests=state.get("quests", []),
        event_log=state.get("event_log", []),
    )
    return {"engine_results": [{"engine": "quest", "completed": completed}]}
