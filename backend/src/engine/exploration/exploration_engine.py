"""Exploration Engine——D20 探索检定 / D20 exploration check."""

import logging

from ...rules.dnd_rules import resolve_check
from ...schemas.request import ExplorationRequest
from ...schemas.response import ExplorationResponse


def resolve_exploration(req: ExplorationRequest) -> ExplorationResponse:
    logging.getLogger("aw.eng").info("[exploration]")
    """探索检定——感知察觉 / Wisdom (Perception) check."""
    result = resolve_check(bonus=req.attribute_mod, dc=req.dc)
    return ExplorationResponse(
        success=result.success,
        result={
            "character_id": req.character_id,
            "action_type": req.action_type,
            "roll": result.roll,
            "bonus": req.attribute_mod,
            "dc": req.dc,
            "total": result.total,
            "critical": result.is_critical,
            "fumble": result.is_fumble,
        },
    )
