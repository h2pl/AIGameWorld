"""故事领域模型 / Story Domain Models."""
from pydantic import BaseModel, Field


class BranchPoint(BaseModel):
    """剧情分支点."""

    tick: int
    decision_maker: str
    decision: str
    consequence: str
    arc_direction: str = ""


class StoryArc(BaseModel):
    """剧情线进度——数据结构，非状态机."""

    id: str
    type: str = "main"
    title: str = ""
    stage: str = "铺陈"
    main_cast: list[str] = Field(default_factory=list)
    supporting_actors: list[str] = Field(default_factory=list)
    key_event_ticks: list[int] = Field(default_factory=list)
    branching_points: list[BranchPoint] = Field(default_factory=list)
    status: str = "setup"


class StoryHook(BaseModel):
    """伏笔追踪."""

    id: str
    planted_tick: int = 0
    description: str = ""
    intended_payoff: str = ""
    urgency: int = 10
    status: str = "planted"


class Quest(BaseModel):
    """任务——DM 生成，主角团尝试完成."""

    id: str
    arc_id: str | None = None
    title: str = ""
    description: str = ""
    status: str = "inactive"
    progress: dict = Field(default_factory=dict)
    assigned_pcs: list[str] = Field(default_factory=list)
    created_tick: int | None = None
    completed_tick: int | None = None


class CastChangeEvent(BaseModel):
    """主角团花名册变动事件."""

    tick: int
    character_id: str
    event_type: str
    reason: str = ""
    arc_id: str | None = None


class MainCastRoster(BaseModel):
    """主角团花名册——追踪变动历史."""

    current_members: list[str] = Field(default_factory=list)
    history: list[CastChangeEvent] = Field(default_factory=list)
