"""OverallState + 子图 State 定义 / Root + subgraph state definitions."""

from typing import Any, TypedDict


class OverallState(TypedDict, total=False):
    """根状态——贯穿整个 tick 图 / Root state — flows through entire tick graph.

    初始时只传入 tick 和 world_id，其余字段由各节点逐步填充。
    pc_decisions / pending_actions 不使用累加器，避免节点重试/子图异常时重复累积。

    WARNING: scene_info 只做一次初始化写入，不会在 tick 内更新。
    PC/Actor 的所有信息（身份+坐标）请从 pc_state_map / actor_state_map 读取，
    这两个 map 是 tick 内唯一权威数据源（repo 只在 tick 末尾才入库）。
    scene_info 仅用于：scene（场景静态属性）、scene_objects（场景物体列表）。
    """

    tick: int
    world_id: str
    hints: list[str]
    plot_brief: str
    scene_id: str
    scene_info: dict[str, Any]  # 仅用于 scene + scene_objects（初始化写入，tick 内不更新）
    pc_decisions: list[dict[str, Any]]
    pending_actions: list[dict[str, Any]]
    narrative: str
    # PC 运行时状态 — tick 内权威数据源，model_dump() 全量写入
    pc_state_map: dict[str, dict[str, Any]]
    # Actor 运行时状态 — 只读，tick 内权威数据源，model_dump() 全量写入
    actor_state_map: dict[str, dict[str, Any]]
    _pending_events: list[dict[str, Any]]
    _dm_ext: dict[str, Any] | None


class PcSubState(TypedDict):
    """角色子图状态 / Character subgraph state.

    WARNING: scene_info 仅做初始化写入，tick 内不更新。获取 PC 数据请用 pc_state_map。
    """

    tick: int
    plot_brief: str
    scene_info: dict[str, Any]  # 仅 scene + scene_objects 可靠，pcs/actors 从 state maps 获取
    pending_actions: list[dict[str, Any]]
    pc_decisions: list[dict[str, Any]]


class PcAgentState(TypedDict):
    """单角色代理状态 / Single character agent state."""

    pc_id: str
    pc_type: str
    plot_brief: str
    tick: int
    pc_decisions: list[dict[str, Any]]


class ReflectionSubState(TypedDict):
    """反思子图状态 / Reflection subgraph state."""

    tick: int
    pc_id: str
    memories: list[dict[str, Any]]
    tick_events: list[dict[str, Any]]
    reflected_pcs: list[str]
    summary_compressed: bool


class EngineSubState(TypedDict, total=False):
    """引擎适配状态 / Engine adapter state."""

    round: int
    participants: list[Any]
    quests: list[Any]
    event_log: list[Any]
