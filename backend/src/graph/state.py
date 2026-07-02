"""OverallState + 子图 State 定义 / Root + subgraph state definitions."""

# LangGraph 累加器 / LangGraph reducer
from operator import add

# 类型标注 / Type annotations
from typing import Annotated, Any, TypedDict


class OverallState(TypedDict):
    """根状态——贯穿整个 tick 图 / Root state — flows through entire tick graph."""

    tick: int  # 当前 tick 编号 / Current tick number
    world_id: str  # 世界 ID / World ID
    tick_message_id: str  # 消息 ID / Message ID
    perceived_character_contexts: list[
        dict[str, Any]
    ]  # 每个角色的感知上下文 / Per-character perceived contexts
    hints: list[str]  # DM 环境提示 / DM environmental hints
    plot_brief: str  # 剧情梗概 / Plot brief
    scene_id: str  # 当前场景 ID / Current scene ID
    character_actions: Annotated[
        list[dict[str, Any]], add
    ]  # 角色行动（累加） / Character actions (accumulated)
    narrative: str  # DM 叙事文本 / DM narrative text
    reflected_characters: list[str]  # 已反思角色 / Reflected character IDs
    summary_compressed: bool  # 是否已摘要压缩 / Whether summary compressed
    errors: Annotated[list[str], add]  # 错误列表（累加） / Error list (accumulated)
    needs_reflection: bool  # 是否需要反思 / Whether reflection is needed


class CharacterSubState(TypedDict):
    """角色子图状态 / Character subgraph state."""

    tick: int
    plot_brief: str
    perceived_character_contexts: list[dict[str, Any]]
    character_actions: Annotated[list[dict[str, Any]], add]


class CharacterAgentState(TypedDict):
    """单角色代理状态 / Single character agent state."""

    character_id: str
    character_type: str  # pc / actor / Player character or NPC
    plot_brief: str
    tick: int
    character_actions: Annotated[list[dict[str, Any]], add]


class ReflectionSubState(TypedDict):
    """反思子图状态 / Reflection subgraph state."""

    tick: int
    character_id: str
    memories: list[dict[str, Any]]
    tick_events: list[dict[str, Any]]
    reflected_characters: list[str]
    summary_compressed: bool


class EngineSubState(TypedDict, total=False):
    """引擎适配状态 / Engine adapter state."""

    round: int
    participants: list[Any]
    quests: list[Any]
    event_log: list[Any]
