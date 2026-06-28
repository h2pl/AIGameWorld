"""Dialogue Service: State ↔ Engine adapter."""
from typing import Any
from ..schemas.request import DialogueRequest
from ..engine.dialogue.dialogue import resolve_dialogue as _resolve_dialogue
from ..graph.state import EngineSubState


def dialogue(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 对话检定."""
    result = _resolve_dialogue(DialogueRequest(
        speaker=state.get("speaker", ""),
        target=state.get("target", ""),
        intent=state.get("intent", ""),
    ))
    return {"engine_results": [{"engine": "dialogue", "result": result.model_dump()}]}
