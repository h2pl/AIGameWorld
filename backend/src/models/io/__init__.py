"""IO 模型：Engine 输入 / 输出契约

Service ↔ Engine 的接口类型，每个文件对应一个 Engine 模块。
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
