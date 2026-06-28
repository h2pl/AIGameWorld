"""OverallState + 子图 State 定义 / Root + subgraph state definitions.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

from typing import TypedDict, Annotated, Any
from operator import add


# ============================================================
# OverallState: 主图状态 / Main graph state
# ============================================================
class OverallState(TypedDict):
    """7 Phase 主图状态 / 7-phase main graph state."""

    tick: int  # 当前 tick 号 / Current tick number

    # Phase 1: DM 创造情境 / DM creates context
    dm_instructions: list[dict[str, Any]]
    plot_brief: str
    scene_direction: dict[str, Any]

    # Phase 2: WorldEngine / World engine execution
    world_events: Annotated[list[dict[str, Any]], add]

    # Phase 3: 角色决策 / Character decisions
    character_actions: Annotated[list[dict[str, Any]], add]

    # Phase 4: Engine 裁决 / Engine resolution
    engine_results: Annotated[list[dict[str, Any]], add]
    combat_result: dict[str, Any] | None

    # Phase 5: 状态合并 / State merge
    state_diff: dict[str, Any]
    cast_changes: list[dict[str, Any]]

    # Phase 6: DM 叙事 / DM narration
    narrative: str

    # Phase 7: 反思 + 摘要 / Reflection + summary
    reflected_characters: list[str]
    summary_compressed: bool

    # 控制 / Control
    errors: Annotated[list[str], add]
    needs_reflection: bool


# ============================================================
# SubState: 各子图专属状态 / Subgraph-specific state schemas
# ============================================================
class CharacterSubState(TypedDict):
    """Phase 3: 角色决策子图 / Character decision subgraph."""
    tick: int
    plot_brief: str
    scene_direction: dict[str, Any]
    character_actions: Annotated[list[dict[str, Any]], add]


class EngineSubState(TypedDict):
    """Phase 4: Engine 裁决子图 / Engine resolution subgraph."""
    participants: list[str]
    round: int
    speaker: str
    target: str
    intent: str
    character_id: str
    action_type: str
    quests: list[dict[str, Any]]
    event_log: list[dict[str, Any]]
    engine_results: Annotated[list[dict[str, Any]], add]
    combat_result: dict[str, Any] | None


class ReflectionSubState(TypedDict):
    """Phase 7: 反思 + 摘要子图 / Reflection + summary subgraph."""
    tick: int
    character_id: str
    memories: list[dict[str, Any]]
    events: list[dict[str, Any]]
    reflected_characters: list[str]
    summary_compressed: bool
