"""DM Engine: 纯业务逻辑."""

from ...schemas.request import DMCreateRequest, DMNarrateRequest
from ...schemas.response import DMCreateResponse, DMNarrateResponse
from ...domain.entities.instruction import DMInstruction


def dm_create(req: DMCreateRequest) -> DMCreateResponse:
    """Phase 1: DM 创造情境. Mock. M4 接入 LLM."""
    dm = DMInstruction.from_request(req)
    return dm.to_response()


def dm_narrate(req: DMNarrateRequest) -> DMNarrateResponse:
    """Phase 6: DM 叙事. Mock. M4 接入 LLM."""
    return DMNarrateResponse(
        narrative_out=f"[DM Narrative] {req.plot_brief} (Actions: {len(req.character_actions)})",
    )
