"""DM 模型：Engine 输入 / 输出类型"""
from typing import TypedDict, Any


class DMCreateInput(TypedDict):
    """Phase 1: DM 创造情境的 Engine 输入"""
    tick: int
    plot_brief: str


class DMCreateOutput(TypedDict):
    """Phase 1: DM 创造情境的 Engine 输出"""
    instructions_out: list[dict[str, Any]]
    plot_brief: str
    scene_direction: dict[str, Any]


class DMNarrateInput(TypedDict):
    """Phase 6: DM 叙事的 Engine 输入"""
    tick: int
    plot_brief: str
    dm_instructions: list[dict[str, Any]]
    scene_direction: dict[str, Any]
    character_actions: list[dict[str, Any]]


class DMNarrateOutput(TypedDict):
    """Phase 6: DM 叙事的 Engine 输出"""
    narrative_out: str
