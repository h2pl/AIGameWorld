"""DM 模型：Engine 输入 / 输出"""
from typing import Any
from pydantic import BaseModel


class DMCreateInput(BaseModel):
    """Phase 1: DM 创造情境的 Engine 输入"""
    tick: int = 0
    plot_brief: str = ""


class DMCreateOutput(BaseModel):
    """Phase 1: DM 创造情境的 Engine 输出"""
    instructions_out: list[dict[str, Any]] = []
    plot_brief: str = ""
    scene_direction: dict[str, Any] = {}


class DMNarrateInput(BaseModel):
    """Phase 6: DM 叙事的 Engine 输入"""
    tick: int = 0
    plot_brief: str = ""
    dm_instructions: list[dict[str, Any]] = []
    scene_direction: dict[str, Any] = {}
    character_actions: list[dict[str, Any]] = []


class DMNarrateOutput(BaseModel):
    """Phase 6: DM 叙事的 Engine 输出"""
    narrative_out: str = ""
