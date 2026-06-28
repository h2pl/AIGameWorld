"""Exploration Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.engine import ExplorationInput, ExplorationOutput


def resolve_exploration(input: ExplorationInput) -> ExplorationOutput:
    """探索检定 / Exploration check. Mock."""
    return ExplorationOutput()
