"""WorldState and related Pydantic models.

Based on docs/06-data-layer.md §5.1.
Architecture spec §10 (WorldState).
"""

from pydantic import BaseModel, Field

from .character import PlayerCharacter, Actor
from .item import Item
from .scene_object import SceneObject
from .story import Quest, StoryArc, StoryHook, MainCastRoster
from .event import Event


class Scene(BaseModel):
    id: str
    name: str
    type: str = "village"  # village / forest / dungeon / castle / capital
    description: str = ""
    exits: list[dict] = Field(default_factory=list)
    landmarks: list[dict] = Field(default_factory=list)
    environment: dict = Field(default_factory=dict)
    pack_name: str = ""


class Faction(BaseModel):
    id: str
    name: str = ""
    leader_character_id: str | None = None
    influence: float = 0.5
    members: list[str] = Field(default_factory=list)
    allies: list[str] = Field(default_factory=list)
    enemies: list[str] = Field(default_factory=list)


class WorldState(BaseModel):
    """Single source of truth for world state. Held in memory by orchestration layer."""

    tick: int = 0
    current_world: str = ""
    current_scene: str = ""

    scenes: dict[str, Scene] = Field(default_factory=dict)

    # ---- Three scene entity types ----
    player_characters: dict[str, PlayerCharacter] = Field(default_factory=dict)
    actors: dict[str, Actor] = Field(default_factory=dict)
    scene_objects: dict[str, SceneObject] = Field(default_factory=dict)
    main_cast: MainCastRoster = Field(default_factory=MainCastRoster)

    # ---- Item system ----
    items: dict[str, Item] = Field(default_factory=dict)

    # ---- Story state ----
    story_arcs: list[StoryArc] = Field(default_factory=list)
    story_hooks: list[StoryHook] = Field(default_factory=list)

    # ---- World state ----
    quests: list[Quest] = Field(default_factory=list)
    factions: dict[str, Faction] = Field(default_factory=dict)
    weather: str = "normal"
    time_of_day: str = "day"

    # ---- Logs ----
    event_log: list[Event] = Field(default_factory=list)
    narrative_log: list[str] = Field(default_factory=list)
    last_plot_brief: str = ""
