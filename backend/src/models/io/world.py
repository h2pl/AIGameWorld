"""World IO：Engine 输入 / 输出"""
from typing import Any
from pydantic import BaseModel


class WorldInput(BaseModel):
    """Phase 2: WorldEngine 的 Engine 输入"""
    tick: int = 0
    dm_instructions: list[dict[str, Any]] = []


class WorldOutput(BaseModel):
    """Phase 2: WorldEngine 的 Engine 输出"""
    events_out: list[dict[str, Any]] = []
