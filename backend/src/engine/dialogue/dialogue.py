"""Dialogue Engine——D20 对话检定 / D20 dialogue check.

通用社交检定，支持说服/欺瞒/威吓/表演/洞悉等 / Generic social check (persuasion/deception/intimidation/performance/insight).
"""

from ...rules.dnd_rules import resolve_check
from ...schemas.request import DialogueRequest
from ...schemas.response import DialogueResponse


def resolve_dialogue(req: DialogueRequest) -> DialogueResponse:
    """对话检定——基础 D20 检定 / Basic D20 social check."""
    if not req.speaker:
        return DialogueResponse(success=False, content="无效对话者。")
    result = resolve_check(bonus=req.attribute_mod, dc=req.dc)
    intent = req.intent or "检定"
    return DialogueResponse(
        success=result.success,
        content=(
            f"'{req.speaker}' {intent} '{req.target}': "
            f"{'成功' if result.success else '失败'} (掷骰={result.roll}+{req.attribute_mod}={result.total} vs DC={req.dc})"
        ),
    )
