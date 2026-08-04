"""OverallState + 子图 State 定义 / Root + subgraph state definitions."""

from typing import TypedDict

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
    world_id: str  # world 标识 / world identifier
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
    pcs_snapshot: dict[str, dict]  # tick_init 截屏的 PC 数据（flush_events 构建 scene_setup 用）


class ReflectionSubState(TypedDict):
    """反思子图状态 / Reflection subgraph state.

    注意：当前主图所有子图（load_data / tick_init / pc）均直接编译
    OverallState，未使用独立子图状态类。本类型保留供未来的反思子图
    或 scheduler 反思任务复用，请勿在已接入节点外随意新增子图状态。
    """

    tick: int
    pc_id: str
    memories: list[Memory]
    tick_events: list[TickEvent]
    reflected_pcs: list[str]
    summary_compressed: bool
