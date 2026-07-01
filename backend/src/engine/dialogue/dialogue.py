"""Dialogue Engine——社交检定 / Social skill check.

注意：普通对话（talk）不需要检定，只有说服/欺瞒/威吓等影响他人的行为才掷 D20。
Ordinary conversation doesn't roll dice — only persuasion/intimidation/deception checks do.
"""
import logging

from ...rules.dnd_rules import resolve_check
from ...schemas.request import DialogueRequest
from ...schemas.response import DialogueResponse


def resolve_persuasion(req: DialogueRequest) -> DialogueResponse:
    logging.getLogger("aw.eng").info("[dialogue]")
    """社交检定——D20 + 修正 vs DC / Social skill check."""
    if not req.speaker:
        return DialogueResponse(success=False, content="无效角色。")
    result = resolve_check(bonus=req.attribute_mod, dc=req.dc)
    intent = req.intent or "说服"
    return DialogueResponse(
        success=result.success,
        content=(
            f"'{req.speaker}' {intent} '{req.target}': "
            f"{'成功' if result.success else '失败'} (掷骰={result.roll}+{req.attribute_mod}={result.total} vs DC={req.dc})"
        ),
    )
