"""OverallState + 子图 State 定义 / Root + subgraph state definitions."""

from typing import Any, TypedDict

from ..domain import (
    Action,
    Actor,
    Decision,
    DMRecord,
    Memory,
    PlayerCharacter,
    Scene,
    SceneObject,
    TickEvent,
    World,
)


class OverallState(TypedDict, total=False):
    """根状态——贯穿整个 tick 图 / Root state — flows through entire tick graph.

    初始时只传入 tick 和 world_id，其余字段由各节点逐步填充。

    字段说明 / Field reference：
    - tick / world_id          — tick 序号 + world 标识（入口传入）
    - world                    — World 领域模型（load_data 从 DB 加载）
    - dm_record                — DM 产出完整记录（dm_create 写入）
    - scene                    — 当前场景（dm_create 选定 id，load_data 加载领域模型）
    - scene_objects            — 当前场景物体列表（load_data 加载）
    - pcs / actors             — 运行时实体 map，tick 内权威数据源（load_data 加载）
    - pc_decisions / actions   — PC 决策 + 行动（pc_subgraph 产出）
    - memories                 — 本 tick 新记忆（引擎写入，persist_tick 落盘）
    - tick_events              — tick 事件列表（event_service 构造，persist_tick 落盘）
    """

    tick: int
    world: World  # 世界观领域模型 / world domain model

    dm_record: DMRecord | None  # DM 产出完整记录 / DM output record

    scene: Scene  # 场景领域模型 / scene domain model
    scene_objects: list[SceneObject]  # 场景物体列表 / scene object list

    pc_decisions: list[Decision]  # PC 决策列表 / PC decision list
    actions: list[Action]  # 行动列表 / action list

    pcs: dict[str, PlayerCharacter]  # PC 运行时状态 / PC runtime state
    actors: dict[str, Actor]  # Actor 运行时状态 / Actor runtime state
    memories: dict[str, list[Memory]]  # 本 tick 新记忆 / new memories this tick

    tick_events: list[TickEvent]  # tick 事件列表 / tick event list


class PcSubState(TypedDict):
    """角色子图状态 / Character subgraph state.

    scene / scene_objects 仅做初始化写入，tick 内不更新。
    获取 PC 数据请用 pcs，获取 Actor 数据请用 actors。
    """

    tick: int
    plot_brief: str
    scene: Scene
    scene_objects: list[SceneObject]
    actions: list[Action]
    pc_decisions: list[Decision]


class PcAgentState(TypedDict):
    """单角色代理状态 / Single character agent state."""

    pc_id: str
    pc_type: str
    plot_brief: str
    tick: int
    pc_decisions: list[Decision]


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
