"""Dialogue Node: State <-> Service glue / 对话节点：State ↔ Service 胶水。"""
from typing import Any
from ..engine.dialogue.dialogue import resolve_dialogue


def dialogue_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 4: 对话检定 / Dialogue check.

    产出 / Outputs: check_result
    """
    result = resolve_dialogue(
        speaker=state.get("speaker", ""),
        target=state.get("target", ""),
        intent=state.get("intent", ""),
    )
    return {"check_result": result}
