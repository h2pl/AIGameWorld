"""Dialogue Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.io.engine import DialogueInput, DialogueOutput


def resolve_dialogue(input: DialogueInput) -> DialogueOutput:
    """对话检定 / Dialogue check. Mock."""
    return DialogueOutput()
