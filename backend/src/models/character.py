"""Character 模型：Engine 输入 / 输出"""
from pydantic import BaseModel


class PCDecideInput(BaseModel):
    """Phase 3: 单个 PC 决策的 Engine 输入"""
    pc_id: str = ""
    plot_brief: str = ""
    tick: int = 0


class PCDecideOutput(BaseModel):
    """Phase 3: 单个 PC 决策的 Engine 输出"""
    character_id: str = ""
    type: str = ""
    description: str = ""


class ActorDecideInput(BaseModel):
    """Phase 3: 单个 Actor 决策的 Engine 输入"""
    actor_id: str = ""
    plot_brief: str = ""
    tick: int = 0


class ActorDecideOutput(BaseModel):
    """Phase 3: 单个 Actor 决策的 Engine 输出"""
    character_id: str = ""
    type: str = ""
    description: str = ""
