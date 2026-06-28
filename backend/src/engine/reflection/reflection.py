"""Reflection Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class ReflectionSubState(TypedDict):
    """Reflection Service 内部数据契约 / Reflection service internal data contract."""
    character_id: str
    memories: list[dict[str, Any]]
    insight_out: str


def reflect(character_id: str, memories: list[dict[str, Any]]) -> str:
    """角色反思 / Character reflection. Mock."""
    return ""
