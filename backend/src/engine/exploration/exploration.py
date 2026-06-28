"""Exploration Engine: 纯业务逻辑."""

from ...schemas.request import ExplorationRequest
from ...schemas.response import ExplorationResponse


def resolve_exploration(req: ExplorationRequest) -> ExplorationResponse:
    """探索检定. Mock."""
    return ExplorationResponse()
