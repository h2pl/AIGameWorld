"""Story-related Pydantic models.

Based on docs/06-data-layer.md §5.2d.
Architecture spec §6.3-6.6 (StoryArc, StoryHook, BranchPoint, MainCastRoster).
"""

from pydantic import BaseModel, Field


class BranchPoint(BaseModel):
    """A story branching point caused by a PC decision."""

    tick: int
    decision_maker: str  # PC id
    decision: str  # what was decided
    consequence: str  # resulting consequence
    arc_direction: str = ""  # which direction the story took


class StoryArc(BaseModel):
    """Storyline progress – data structure, not a state machine."""

    id: str
    type: str = "main"  # main / side
    title: str = ""
    stage: str = "\u94fa\u9648"  # 铺陈 / 发展 / 冲突升级 / 高潮 / 收尾
    main_cast: list[str] = Field(default_factory=list)
    supporting_actors: list[str] = Field(default_factory=list)
    key_event_ticks: list[int] = Field(default_factory=list)
    branching_points: list[BranchPoint] = Field(default_factory=list)
    status: str = "setup"  # setup / active / climax / resolved / abandoned


class StoryHook(BaseModel):
    """Foreshadowing tracker."""

    id: str
    planted_tick: int = 0
    description: str = ""
    intended_payoff: str = ""
    urgency: int = 10
    status: str = "planted"  # planted / escalated / paid_off / abandoned


class CastChangeEvent(BaseModel):
    """A change in the main cast roster."""

    tick: int
    character_id: str
    event_type: str  # join / leave / death / betrayal
    reason: str = ""
    arc_id: str | None = None


class Quest(BaseModel):
    """A quest that can be assigned to PCs."""

    id: str
    arc_id: str | None = None
    title: str = ""
    description: str = ""
    status: str = "inactive"  # inactive / active / completed / failed
    progress: dict = Field(default_factory=dict)
    assigned_pcs: list[str] = Field(default_factory=list)
    created_tick: int | None = None
    completed_tick: int | None = None


class MainCastRoster(BaseModel):
    """Main cast roster – tracks membership changes over time."""

    current_members: list[str] = Field(default_factory=list)
    history: list[CastChangeEvent] = Field(default_factory=list)
