"""WorldEngine 子图 / World Engine Subgraph.
Phase 2: 执行 DM 指令 / Execute DM instructions.
Mock: 空事件列表. 后续 M6 接入 / Mock: empty events. M6 integration.
"""

from typing import TypedDict, Any


class WorldEngineSubState(TypedDict):
    """WorldEngine 子图状态 / WorldEngine subgraph state."""
    instructions: list[dict[str, Any]]
    world_snapshot: dict[str, Any]
    events_out: list[dict[str, Any]]


def execute_dm_instructions(state: dict[str, Any]) -> WorldEngineSubState:
    """Phase 2: 执行 DM 指令（场景实例化、Actor 动机注入等）.
    
    Mock: 空事件列表.
    """
    return WorldEngineSubState(
        instructions=state.get("instructions", []),
        world_snapshot=state.get("world_snapshot", {}),
        events_out=[],  # 无世界变化 / No world changes yet
    )
