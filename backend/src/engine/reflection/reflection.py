"""Reflection Engine: 纯业务逻辑."""

from ...schemas.request import ReflectionRequest
from ...schemas.response import ReflectionResponse


def reflect(req: ReflectionRequest) -> ReflectionResponse:
    """角色反思. Mock. Phase 3 接入 LLM."""
    return ReflectionResponse(insights_out=[{
        "character_id": req.character_id or "unknown",
        "memories_count": len(req.memories),
        "insight": "Mock: No deep reflections formed yet.",
    }])
