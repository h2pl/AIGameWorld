"""角色行动领域模型 / Action Domain Model."""
from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ...schemas.request import PCDecideRequest, ActorDecideRequest
    from ...schemas.response import PCDecideResponse, ActorDecideResponse


class Action(BaseModel):
    """角色行动——Agent 输出 → 规则引擎输入."""

    character_id: str
    character_type: str = "pc"
    tick: int = 0
    action_type: str = "wait"
    target: str | None = None
    reasoning: str = ""
    params: dict = Field(default_factory=dict)

    @classmethod
    def from_pc_request(cls, req: PCDecideRequest) -> Action:
        """Schema Request → Domain Model"""
        return cls(
            character_id=req.pc_id,
            character_type="pc",
            tick=req.tick,
            action_type="explore",
            reasoning=f"PC {req.pc_id} deciding based on: {req.plot_brief}",
        )

    @classmethod
    def from_actor_request(cls, req: ActorDecideRequest) -> Action:
        """Schema Request → Domain Model"""
        return cls(
            character_id=req.actor_id,
            character_type="actor",
            tick=req.tick,
            action_type="idle",
            reasoning=f"Actor {req.actor_id} deciding based on: {req.plot_brief}",
        )

    def to_pc_response(self) -> PCDecideResponse:
        """Domain Model → Schema Response"""
        from ...schemas.response import PCDecideResponse
        return PCDecideResponse(
            character_id=self.character_id,
            type=self.action_type,
            description=self.reasoning,
        )

    def to_actor_response(self) -> ActorDecideResponse:
        """Domain Model → Schema Response"""
        from ...schemas.response import ActorDecideResponse
        return ActorDecideResponse(
            character_id=self.character_id,
            type=self.action_type,
            description=self.reasoning,
        )
