"""DialogueEngine 子图 / Dialogue Engine Subgraph.
Phase 4: D20 对话检定 / D20 dialogue check.
Mock: 返回空结果. 后续 M6 接入 / Mock: empty result. M6 integration.
"""

from typing import TypedDict, Any


class DialogueSubState(TypedDict):
    """DialogueEngine 子图状态 / DialogueEngine subgraph state."""
    speaker: str  # 说话者 / Speaker ID
    target: str  # 目标 / Target ID
    intent: str  # 意图：persuade/deceive/intimidate / Intent
    content: str  # 对话内容 / Dialogue content
    check_result: dict[str, Any]  # 检定结果 / Check result


def resolve_dialogue(state: dict[str, Any]) -> DialogueSubState:
    """解析对话检定 / Resolve dialogue check.
    
    Mock: 空检定结果.
    """
    return DialogueSubState(
        speaker=state.get("speaker", ""),
        target=state.get("target", ""),
        intent=state.get("intent", "persuade"),
        content=state.get("content", ""),
        check_result={},  # 空检定 / No check result yet
    )
