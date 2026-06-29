"""Dialogue Engine——D20 对话检定 / D20 dialogue check."""

from ...rules.dnd_rules import resolve_check
from ...schemas.request import DialogueRequest
from ...schemas.response import DialogueResponse


def resolve_dialogue(req: DialogueRequest) -> DialogueResponse:
    """对话检定——魅力说服 / Charisma (Persuasion) check."""
    if not req.speaker:
        return DialogueResponse(success=False, content="无效对话者。")
    result = resolve_check(bonus=req.attribute_mod, dc=req.dc)
    return DialogueResponse(
        success=result.success,
        content=f"'{req.speaker}' {'成功' if result.success else '未能'} 说服 '{req.target}' (掷骰={result.roll} vs DC={req.dc})",
        errors=[f"说服检定 {'成功' if result.success else '失败'}, 掷骰={result.roll}, 总计={result.total}"] if not result.success else [],
    )
