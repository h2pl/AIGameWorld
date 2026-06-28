"""World Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class WorldInput(TypedDict):
    """Phase 2: WorldEngine 的 Engine 输入"""
    tick: int
    dm_instructions: list[dict[str, Any]]


def execute_instructions(input: WorldInput) -> dict:
    """执行 DM 指令 / Execute DM instructions. Mock. M6 接入场景实例化."""
    return {"events_out": []}
