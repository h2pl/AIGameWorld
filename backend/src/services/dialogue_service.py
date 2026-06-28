"""Dialogue Service: State ↔ Engine adapter."""
from typing import Any
from ..models.engine import DialogueInput
from ..engine.dialogue.dialogue import resolve_dialogue as _resolve_dialogue
from ..graph.state import EngineSubState


def _to_dialogue_input(state: EngineSubState) -> DialogueInput:
    return {"speaker": state.get("speaker", ""), "target": state.get("target", ""), "intent": state.get("intent", "")}


def dialogue(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 对话检定. 产出 / Outputs: engine_results"""
    result = _resolve_dialogue(_to_dialogue_input(state))
    return {"engine_results": [{"engine": "dialogue", "result": result}]}
