"""OverallState + 子图 State 定义 / Root + subgraph state definitions."""

# 类型标注 / Type annotations
from typing import Any, TypedDict


class OverallState(TypedDict, total=False):
    """根状态——贯穿整个 tick 图 / Root state — flows through entire tick graph.

    初始时只传入 tick 和 world_id，其余字段由各节点逐步填充。
    pc_decisions / pending_actions 不使用累加器，避免节点重试/子图异常时重复累积。
    """

    tick: int  # 当前 tick 编号 / Current tick number
    world_id: str  # 世界 ID / World ID
    hints: list[str]  # DM 环境提示 / DM environmental hints
    plot_brief: str  # 剧情梗概 / Plot brief
    scene_id: str  # 当前场景 ID / Current scene ID
    scene_info: dict[str, Any]  # 当前场景的信息 / Current scene info
    pc_decisions: list[dict[str, Any]]  # 角色决策 / Character decisions
    pending_actions: list[dict[str, Any]]  # pc_subgraph 产生的行动结果
    narrative: str  # DM 叙事文本 / DM narrative text
    # PC 运行时状态——tick 内引擎修改此 map，末尾统一入库
    pc_state_map: dict[str, dict[str, Any]]
    # Actor 运行时状态——只读，用于查询 actor 坐标 / Actor runtime state — read-only, for position lookup
    actor_state_map: dict[str, dict[str, Any]]
    # flush_events 产出的待持久化事件列表 / Pending events for persistence
    _pending_events: list[dict[str, Any]]
    # dm_create 产出的 LLM 原始输出，供 persist_tick 落 dm_records
    _dm_ext: dict[str, Any] | None


class PcSubState(TypedDict):
    """角色子图状态 / Character subgraph state."""

    tick: int
    plot_brief: str
    scene_info: dict[str, Any]
    pending_actions: list[dict[str, Any]]
    pc_decisions: list[dict[str, Any]]


class PcAgentState(TypedDict):
    """单角色代理状态 / Single character agent state."""

    pc_id: str
    pc_type: str  # pc / actor / Player character or NPC
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
