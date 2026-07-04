"""OverallState + 子图 State 定义 / Root + subgraph state definitions."""

# LangGraph 累加器 / LangGraph reducer
from operator import add

# 类型标注 / Type annotations
from typing import Annotated, Any, TypedDict


class OverallState(TypedDict, total=False):
    """根状态——贯穿整个 tick 图 / Root state — flows through entire tick graph.

    初始时只传入 tick 和 world_id，其余字段由各节点逐步填充。
    """

    tick: int  # 当前 tick 编号 / Current tick number
    tick_message_id: str  # 消息 ID / Message ID
    world_id: str  # 世界 ID / World ID
    hints: list[str]  # DM 环境提示 / DM environmental hints
    plot_brief: str  # 剧情梗概 / Plot brief
    scene_id: str  # 当前场景 ID / Current scene ID
    scene_info: dict[
        str, Any
    ]  # 当前场景的信息（与谁使用无关，不区分 PC）/ Current scene info (consumer-independent, not per-PC)
    pc_decisions: Annotated[
        list[dict[str, Any]], add
    ]  # 角色决策（累加） / Character decisions (accumulated)
    pending_actions: Annotated[list[dict[str, Any]], add]  # pc_subgraph 产生的行动结果（累加）
    narrative: str  # DM 叙事文本 / DM narrative text


class PcSubState(TypedDict):
    """角色子图状态 / Character subgraph state."""

    tick: int
    plot_brief: str
    scene_info: dict[str, Any]
    pending_actions: Annotated[list[dict[str, Any]], add]
    pc_decisions: Annotated[list[dict[str, Any]], add]


class PcAgentState(TypedDict):
    """单角色代理状态 / Single character agent state."""

    pc_id: str
    pc_type: str  # pc / actor / Player character or NPC
    plot_brief: str
    tick: int
    pc_decisions: Annotated[list[dict[str, Any]], add]


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
