"""Quest Service: State ↔ Engine adapter / 任务服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.quest.quest import check_quests as _check_quests
from ..graph.state import EngineSubState


def _to_quest_input(state: EngineSubState) -> dict[str, Any]:
    """① State → Engine 输入"""
    return {
        "quests": state.get("quests", []),
        "event_log": state.get("event_log", []),
    }


def quest(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 任务检查 / Quest completion check.

    ① State → Engine 输入
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: engine_results
    """
    engine_input = _to_quest_input(state)                            # ①
    completed = _check_quests(**engine_input)                         # ②
    return {"engine_results": [{"engine": "quest", "completed": completed}]}  # ③

