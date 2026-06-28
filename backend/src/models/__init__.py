"""AIGameWorld 数据模型

├── io/                  Engine 输入/输出契约（Service ↔ Engine 的接口类型）
│   ├── dm.py            DMCreateInput/Output, DMNarrateInput/Output
│   ├── world.py         WorldInput/Output
│   ├── character.py     PCDecideInput/Output, ActorDecideInput/Output
│   ├── engine.py        Combat/Dialogue/Exploration/Quest Input/Output
│   └── reflection.py    ReflectionInput, SummarizerInput
│
├── instruction.py       DM 指令领域模型（DMInstruction, PlotEvent 等）
├── action.py            角色行动领域模型（Action）
├── event.py             世界事件领域模型（Event）
├── story.py             故事领域模型（StoryArc, Quest, StoryHook 等）
├── item.py              道具领域模型
├── character.py         角色领域模型
└── scene_object.py      场景物体领域模型
"""

from .io import (
    DMCreateInput, DMCreateOutput, DMNarrateInput, DMNarrateOutput,
    WorldInput, WorldOutput,
    PCDecideInput, PCDecideOutput, ActorDecideInput, ActorDecideOutput,
    CombatInput, CombatOutput, DialogueInput, DialogueOutput,
    ExplorationInput, ExplorationOutput, QuestInput,
    ReflectionInput, SummarizerInput,
)

__all__ = [
    "DMCreateInput", "DMCreateOutput", "DMNarrateInput", "DMNarrateOutput",
    "WorldInput", "WorldOutput",
    "PCDecideInput", "PCDecideOutput", "ActorDecideInput", "ActorDecideOutput",
    "CombatInput", "CombatOutput", "DialogueInput", "DialogueOutput",
    "ExplorationInput", "ExplorationOutput", "QuestInput",
    "ReflectionInput", "SummarizerInput",
]
