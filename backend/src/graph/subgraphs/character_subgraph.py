"""Character Agent Subgraphs: PC + Actor / 角色智能体子图。

Node 函数由 nodes/ 层提供, Service 由 engine/ 层提供。
"""
from langgraph.graph import StateGraph, END
from ...nodes.character_nodes import pc_decide_node, actor_decide_node


def build_pc_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("pc_decide", pc_decide_node)
    graph.set_entry_point("pc_decide")
    graph.add_edge("pc_decide", END)
    return graph


def build_actor_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("actor_decide", actor_decide_node)
    graph.set_entry_point("actor_decide")
    graph.add_edge("actor_decide", END)
    return graph


pc_subgraph = build_pc_subgraph().compile()
actor_subgraph = build_actor_subgraph().compile()
