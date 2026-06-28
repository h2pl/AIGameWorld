"""World Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class WorldEngineSubState(TypedDict):
    """WorldEngine Service 内部数据契约 / WorldEngine service internal data contract."""
    tick: int
    dm_instructions: list[dict[str, Any]]
    events_out: list[dict[str, Any]]


def execute_instructions(state: WorldEngineSubState) -> dict:
    """执行 DM 指令 / Execute DM instructions. Mock. M6 接入场景实例化."""
    return {"events_out": []}
