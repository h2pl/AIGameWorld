"""Phase 3 子图: 唤醒 PC + Actor 决策。

┌─ entry ──┐
│ pc_decide │  遍历 featured_pcs → character_actions (add)
│actor_decid│  遍历 featured_actors → character_actions (add)
└─── END ───┘
"""

from langgraph.graph import END, StateGraph

from ...services import character_service
from ..state import CharacterSubState


def build_character_subgraph() -> StateGraph:
    graph = StateGraph(CharacterSubState)
    graph.add_node("character_service.pc_decide", character_service.pc_decide)
    graph.add_node("character_service.actor_decide", character_service.actor_decide)
    graph.set_entry_point("character_service.pc_decide")
    graph.add_edge("character_service.pc_decide", "character_service.actor_decide")
    graph.add_edge("character_service.actor_decide", END)
    return graph


character_subgraph = build_character_subgraph().compile()
