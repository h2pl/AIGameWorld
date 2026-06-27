"""世界状态 Pydantic 模型 / WorldState Pydantic model.

基于 docs/06-data-layer.md §5.1 / Based on docs/06-data-layer.md §5.1.
架构方案 §10 (WorldState) / Architecture spec §10.

WorldState 是运行时内存中的唯一真相源 / WorldState is the single source of truth in runtime memory.
所有状态变更必须经编排层调用，数据层不主动改数据。
All state changes go through orchestration layer; data layer does not mutate actively.
"""

from pydantic import BaseModel, Field

from .character import PlayerCharacter, Actor
from .item import Item
from .scene_object import SceneObject
from .story import Quest, StoryArc, StoryHook, MainCastRoster
from .event import Event


class Scene(BaseModel):
    """场景实例（Def 来自 World Pack，Instance 存运行时状态）/ Scene instance."""

    id: str                         # 唯一 ID / Unique ID
    name: str = ""
    type: str = "village"           # village/forest/dungeon/castle/capital
    description: str = ""
    exits: list[dict] = Field(default_factory=list)       # 出口列表 / Exit list
    landmarks: list[dict] = Field(default_factory=list)   # 地标 / Landmarks
    environment: dict = Field(default_factory=dict)       # 环境设置 / Environment (weather/lighting)
    pack_name: str = ""             # 来自哪个 World Pack / Source pack


class Faction(BaseModel):
    """势力——运行时状态 / Faction — runtime state."""

    id: str
    name: str = ""
    leader_character_id: str | None = None    # 首领角色 ID / Leader character ID
    influence: float = 0.5                     # 影响力 0-1 / Influence
    members: list[str] = Field(default_factory=list)   # 成员 / Members
    allies: list[str] = Field(default_factory=list)    # 盟友 / Allies
    enemies: list[str] = Field(default_factory=list)   # 敌人 / Enemies


class WorldState(BaseModel):
    """世界状态——每 Tick 由编排层在内存中持有 / World state — held in memory by orchestration layer."""

    tick: int = 0                       # 当前 tick / Current tick
    current_world: str = ""             # 当前 World Pack 名 / Current World Pack name
    current_scene: str = ""             # 当前场景 ID / Current scene ID

    scenes: dict[str, Scene] = Field(default_factory=dict)  # 场景列表 / Scene list

    # ---- 三类场景实体 / Three scene entity types ----
    player_characters: dict[str, PlayerCharacter] = Field(default_factory=dict)  # 主角团
    actors: dict[str, Actor] = Field(default_factory=dict)                       # 配角
    scene_objects: dict[str, SceneObject] = Field(default_factory=dict)          # 场景对象
    main_cast: MainCastRoster = Field(default_factory=MainCastRoster)            # 花名册

    # ---- 物品系统 / Item system ----
    items: dict[str, Item] = Field(default_factory=dict)  # 全局物品定义

    # ---- 故事状态 / Story state ----
    story_arcs: list[StoryArc] = Field(default_factory=list)    # 剧情线
    story_hooks: list[StoryHook] = Field(default_factory=list)  # 伏笔

    # ---- 世界状态 / World state ----
    quests: list[Quest] = Field(default_factory=list)           # 任务
    factions: dict[str, Faction] = Field(default_factory=dict)  # 势力
    weather: str = "normal"                                     # 天气
    time_of_day: str = "day"                                    # 时段

    # ---- 日志 / Logs ----
    event_log: list[Event] = Field(default_factory=list)        # 事件日志（追加写）
    narrative_log: list[str] = Field(default_factory=list)      # 叙事日志
    last_plot_brief: str = ""                                   # 上轮剧情梗概 / Last plot brief
