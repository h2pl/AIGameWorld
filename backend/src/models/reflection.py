"""Reflection 模型：Engine 输入 / 输出类型"""
from typing import TypedDict, Any


class ReflectionInput(TypedDict):
    """Phase 7: 角色反思的 Engine 输入"""
    character_id: str
    memories: list[dict[str, Any]]


# reflect 返回 str (insight text)，不需要 TypedDict


class SummarizerInput(TypedDict):
    """Phase 7: 事件压缩的 Engine 输入"""
    events: list[dict[str, Any]]
    tick: int


# summarize 返回 str (summary text)，不需要 TypedDict
