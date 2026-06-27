"""CharacterReflection 子图 / Character Reflection Subgraph.
Phase 7: 角色反思（条件触发）/ Character reflection (conditional trigger).
Mock: 返回空结果. 后续 M5 接入 / Mock: empty result. M5 integration.
"""

from typing import TypedDict, Any


class ReflectionSubState(TypedDict):
    """反思子图状态 / Reflection subgraph state."""
    character_id: str  # 角色 ID / Character ID
    memories: list[dict[str, Any]]  # 近期记忆 / Recent memories
    importance_accumulator: float  # 重要性累计 / Importance accumulator
    insight_out: str  # 反思洞察 / Reflection insight


def reflect_on_experiences(state: dict[str, Any]) -> ReflectionSubState:
    """角色反思 / Character reflection.
    
    Mock: 空洞察.
    """
    return ReflectionSubState(
        character_id=state.get("character_id", ""),
        memories=state.get("memories", []),
        importance_accumulator=state.get("importance_accumulator", 0.0),
        insight_out="",  # 无洞察 / No insight yet
    )
