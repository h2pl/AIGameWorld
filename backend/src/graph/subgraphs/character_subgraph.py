"""Character Agent Subgraphs: PC + Actor / 角色智能体子图."""
from langgraph.graph import StateGraph, END

from ...engine.character.pc_decide import PCSubState, pc_decide_node
from ...engine.character.actor_decide import ActorSubState, actor_decide_node


def build_pc_subgraph() -> StateGraph:
    graph = StateGraph(PCSubState)
    graph.add_node("pc_decide", pc_decide_node)
    graph.set_entry_point("pc_decide")
    graph.add_edge("pc_decide", END)
    return graph


def build_actor_subgraph() -> StateGraph:
    graph = StateGraph(ActorSubState)
    graph.add_node("actor_decide", actor_decide_node)
    graph.set_entry_point("actor_decide")
    graph.add_edge("actor_decide", END)
    return graph


pc_subgraph = build_pc_subgraph().compile()
actor_subgraph = build_actor_subgraph().compile()
