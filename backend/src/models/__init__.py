"""AIGameWorld 数据模型：Engine 输入 / 输出类型

Model 层职责: 定义所有跨层共享的数据结构（无依赖 LangGraph / 业务逻辑）
"""

from .dm import DMCreateInput, DMCreateOutput, DMNarrateInput, DMNarrateOutput
from .world import WorldInput, WorldOutput
from .character import PCDecideInput, PCDecideOutput, ActorDecideInput, ActorDecideOutput
from .engine import CombatInput, CombatOutput, DialogueInput, DialogueOutput, ExplorationInput, ExplorationOutput, QuestInput
from .reflection import ReflectionInput, SummarizerInput

__all__ = [
    "DMCreateInput", "DMCreateOutput", "DMNarrateInput", "DMNarrateOutput",
    "WorldInput", "WorldOutput",
    "PCDecideInput", "PCDecideOutput", "ActorDecideInput", "ActorDecideOutput",
    "CombatInput", "CombatOutput", "DialogueInput", "DialogueOutput",
    "ExplorationInput", "ExplorationOutput", "QuestInput",
    "ReflectionInput", "SummarizerInput",
]
