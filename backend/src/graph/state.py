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
)


class OverallState(TypedDict, total=False):
    """根状态——贯穿整个 tick 图 / Root state — flows through entire tick graph.

    初始时只传入 tick 和 world_id，其余字段由各节点逐步填充。
    pc_decisions / actions 不使用累加器，避免节点重试/子图异常时重复累积。

    字段命名统一如下，避免误会：
    - scene: Scene 领域模型（单场景信息，仅初始化写入，tick 内不更新）
    - scene_objects: SceneObject 领域模型列表（仅初始化写入）
    - pcs: PlayerCharacter 领域模型 map — tick 内 PC 权威数据源
    - actors: Actor 领域模型 map — tick 内 Actor 权威数据源
    - pc_decisions: Decision 领域模型列表
    - actions: Action 领域模型列表
    - pc_memory_map: Memory 领域模型列表 map — 本 tick 新记忆
    - _pending_events: TickEvent 领域模型列表 — tick 内产生的事件
    - _dm_ext: DMRecord 领域模型 — DM 产出完整记录
    所有节点按需直接读取/修改领域模型；data_service 在 tick 末尾直接 save() 落盘。
    """

    tick: int
    world_id: str
    hints: list[str]
    plot_brief: str
    scene_id: str
    scene: Scene  # 单场景信息 / single scene context
    scene_objects: list[SceneObject]  # 场景物体列表 / scene object list
    pc_decisions: list[Decision]
    actions: list[Action]
    narrative: str
    # PC 运行时状态 — tick 内权威数据源，领域模型
    pcs: dict[str, PlayerCharacter]
    # Actor 运行时状态 — tick 内权威数据源，领域模型
    actors: dict[str, Actor]
    # 本 tick 各角色产生的新记忆 — 引擎写入，data_service 统一落盘
    pc_memory_map: dict[str, list[Memory]]
    _pending_events: list[TickEvent]
    _dm_ext: DMRecord | None  # DM 产出完整记录


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
