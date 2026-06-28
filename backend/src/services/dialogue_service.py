"""Dialogue Service: State ↔ Engine adapter / 对话服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.dialogue.dialogue import resolve_dialogue as _resolve_dialogue
from ..graph.state import EngineSubState


def dialogue(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 对话检定 / Dialogue check.

    产出 / Outputs: engine_results
    """
    result = _resolve_dialogue(
        speaker=state.get("speaker", ""),
        target=state.get("target", ""),
        intent=state.get("intent", ""),
    )
    return {"engine_results": [{"engine": "dialogue", "result": result}]}
