"""Phase 7 Service: Reflection + Summarizer 协调。"""
from typing import Any

from .reflection_service import reflect
from .summarizer_service import summarize


def reflection_decide(state: dict[str, Any]) -> dict[str, Any]:
    """协调 Reflection + Summarizer。"""
    reflect({"character_id": "", "memories": []})
    summarize({"events": [], "tick": state.get("tick", 0)})
    return {"reflected_characters": [], "summary_compressed": False}
