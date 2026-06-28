"""Quest Node: State <-> Service glue / 任务节点：State ↔ Service 胶水。"""
from typing import Any
from ..engine.quest.quest import check_quests


def quest_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 4: 任务检查 / Quest completion check.

    产出 / Outputs: completed_quests
    """
    completed = check_quests(
        quests=state.get("quests", []),
        event_log=state.get("event_log", []),
    )
    return {"completed_quests": completed}
