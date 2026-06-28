"""Dialogue Service: State ↔ Engine adapter / 对话服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.dialogue.dialogue import DialogueInput, resolve_dialogue as _resolve_dialogue
from ..graph.state import EngineSubState


def _to_dialogue_input(state: EngineSubState) -> DialogueInput:
    """① State → Engine 输入"""
    return {
        "speaker": state.get("speaker", ""),
        "target": state.get("target", ""),
        "intent": state.get("intent", ""),
    }


def dialogue(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 对话检定 / Dialogue check.

    ① State → DialogueInput
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: engine_results
    """
    engine_input = _to_dialogue_input(state)                     # ①
    result = _resolve_dialogue(engine_input)                     # ②
    return {"engine_results": [{"engine": "dialogue", "result": result}]}  # ③
