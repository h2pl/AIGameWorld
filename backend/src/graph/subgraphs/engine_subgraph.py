"""Phase 4 子图: 路由到各 Engine。

┌── entry ──┐
│  combat    │  战斗裁决 → engine_results + combat_result
│  dialogue  │  对话检定 → engine_results (add)
│exploration │  探索检定 → engine_results (add)
│   quest    │  任务检查 → engine_results (add)
└─── END ────┘
"""

from langgraph.graph import END, StateGraph

from ...services import combat_service, dialogue_service, exploration_service, quest_service
from ..state import EngineSubState


def build_engine_subgraph() -> StateGraph:
    graph = StateGraph(EngineSubState)
    graph.add_node("combat_service.combat", combat_service.combat)
    graph.add_node("dialogue_service.dialogue", dialogue_service.dialogue)
    graph.add_node("exploration_service.exploration", exploration_service.exploration)
    graph.add_node("quest_service.quest", quest_service.quest)
    graph.set_entry_point("combat_service.combat")
    graph.add_edge("combat_service.combat", "dialogue_service.dialogue")
    graph.add_edge("dialogue_service.dialogue", "exploration_service.exploration")
    graph.add_edge("exploration_service.exploration", "quest_service.quest")
    graph.add_edge("quest_service.quest", END)
    return graph


engine_subgraph = build_engine_subgraph().compile()
