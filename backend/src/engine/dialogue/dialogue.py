"""Dialogue Engine: 纯业务逻辑."""

from ...schemas.request import DialogueRequest
from ...schemas.response import DialogueResponse


def resolve_dialogue(req: DialogueRequest) -> DialogueResponse:
    """对话检定. Mock."""
    return DialogueResponse()
