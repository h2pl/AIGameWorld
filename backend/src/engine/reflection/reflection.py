"""Reflection Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class ReflectionInput(TypedDict):
    """Phase 7: 角色反思的 Engine 输入"""
    character_id: str
    memories: list[dict[str, Any]]


def reflect(input: ReflectionInput) -> str:
    """角色反思 / Character reflection. Mock."""
    return ""
