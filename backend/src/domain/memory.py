"""记忆领域模型 / Memory domain model.

从 schemas/memory_schema 下沉到 domain，供 state、repo、engine 统一使用。
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class MemoryType(StrEnum):
    """记忆类型 / Memory type."""

    OBSERVATION = "observation"
    TALK = "talk"
    EXPLORE = "explore"
    INTERACT = "interact"
    COMBAT = "combat"
    REFLECTION = "reflection"


class MemoryPeriod(StrEnum):
    """记忆周期 / Memory lifecycle period."""

    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class EntityType(StrEnum):
    """记忆归属实体 / Memory owner entity."""

    PC = "pc"
    ACTOR = "actor"


class Memory(BaseModel):
    """角色记忆条目 / Character memory entry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    pc_id: str
    content: str
    tick: int
    importance: int = 1
    memory_type: str = MemoryType.OBSERVATION.value
    period: str = MemoryPeriod.MEDIUM_TERM.value
    entity_type: str = EntityType.PC.value
    world_id: str = ""


def importance_of(memory_type: str) -> int:
    """根据记忆类型估算重要性 / Estimate memory importance by type.

    用于各引擎写入记忆时统一赋值。
    """

    mapping: dict[str, int] = {
        MemoryType.REFLECTION.value: 10,
        MemoryType.COMBAT.value: 8,
        MemoryType.INTERACT.value: 4,
        MemoryType.TALK.value: 3,
        MemoryType.EXPLORE.value: 2,
        MemoryType.OBSERVATION.value: 1,
    }
    return mapping.get(memory_type, 2)
