"""Reflection IO：Engine 输入"""
from typing import Any
from pydantic import BaseModel


class ReflectionInput(BaseModel):
    """Phase 7: 角色反思的 Engine 输入"""
    character_id: str = ""
    memories: list[dict[str, Any]] = []


class SummarizerInput(BaseModel):
    """Phase 7: 事件压缩的 Engine 输入"""
    events: list[dict[str, Any]] = []
    tick: int = 0
