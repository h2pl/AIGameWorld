"""Exploration Engine: 纯业务逻辑."""

from ...schemas.request import ExplorationRequest
from ...schemas.response import ExplorationResponse


def resolve_exploration(req: ExplorationRequest) -> ExplorationResponse:
    """探索检定. Mock. Phase 5 接入 D20 规则."""
    return ExplorationResponse(
        success=True,
        result={
            "character_id": req.character_id,
            "action_type": req.action_type,
            "description": "mock perception check: passed",
        },
    )
