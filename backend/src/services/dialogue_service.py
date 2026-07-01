"""Dialogue Service: State ↔ Engine adapter."""

import logging

from ..engine.dialogue import dialogue_engine
from ..graph.state import EngineSubState
from ..schemas.request import DialogueRequest


def dialogue(state: EngineSubState) -> dict:
    logging.getLogger("aw.svc").info("[dialogue]")
    """Phase 4: 对话检定 / Social check."""
    result = dialogue_engine.resolve_persuasion(
        DialogueRequest(
            speaker=state.get("speaker", ""),
            target=state.get("target", ""),
            intent=state.get("intent", ""),
        )
    )
    return {"engine_results": [{"engine": "dialogue", "result": result.model_dump()}]}
