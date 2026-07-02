"""记忆领域模型 / Memory domain model."""

from pydantic import BaseModel


class Memory(BaseModel):
    """角色记忆条目 / Character memory entry."""

    id: str
    character_id: str
    content: str
    tick: int
    importance: int = 1
    memory_type: str = "observation"


def importance_of(event_type: str) -> int:
    """根据事件类型估算记忆重要性 / Estimate memory importance by event type."""

    mapping = {
        "character_death": 10,
        "combat_hit": 8,
        "boss_reveal": 9,
        "quest_complete": 7,
        "character_talk": 3,
        "character_explore": 2,
        "move": 1,
    }
    return mapping.get(event_type, 2)
