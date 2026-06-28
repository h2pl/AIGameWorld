"""Character 模型：Engine 输入 / 输出类型"""
from typing import TypedDict, Any


class PCDecideInput(TypedDict):
    """Phase 3: 单个 PC 决策的 Engine 输入"""
    pc_id: str
    plot_brief: str
    tick: int


class PCDecideOutput(TypedDict):
    """Phase 3: 单个 PC 决策的 Engine 输出"""
    character_id: str
    type: str
    description: str


class ActorDecideInput(TypedDict):
    """Phase 3: 单个 Actor 决策的 Engine 输入"""
    actor_id: str
    plot_brief: str
    tick: int


class ActorDecideOutput(TypedDict):
    """Phase 3: 单个 Actor 决策的 Engine 输出"""
    character_id: str
    type: str
    description: str
