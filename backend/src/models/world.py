"""World 模型：Engine 输入 / 输出类型"""
from typing import TypedDict, Any


class WorldInput(TypedDict):
    """Phase 2: WorldEngine 的 Engine 输入"""
    tick: int
    dm_instructions: list[dict[str, Any]]


class WorldOutput(TypedDict):
    """Phase 2: WorldEngine 的 Engine 输出"""
    events_out: list[dict[str, Any]]
