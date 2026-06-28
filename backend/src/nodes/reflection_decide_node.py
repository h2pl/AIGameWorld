"""Phase 7 节点: Reflection + Summarizer 协调。"""
from typing import Any

from .reflection_nodes import reflection_node
from .summarizer_nodes import summarizer_node


def reflection_decide_node(state: dict[str, Any]) -> dict[str, Any]:
    """协调 Reflection + Summarizer。"""
    reflection_node({"character_id": "", "memories": []})
    summarizer_node({"events": [], "tick": state.get("tick", 0)})
    return {"reflected_characters": [], "summary_compressed": False}
