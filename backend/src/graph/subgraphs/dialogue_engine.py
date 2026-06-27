"""Dialogue Engine Subgraph / 对话引擎子图."""
from langgraph.graph import StateGraph, END
from ...engine.dialogue.dialogue import DialogueSubState, resolve_dialogue_node

def build_dialogue_subgraph() -> StateGraph:
    graph = StateGraph(DialogueSubState)
    graph.add_node("dialogue_process", resolve_dialogue_node)
    graph.set_entry_point("dialogue_process")
    graph.add_edge("dialogue_process", END)
    return graph

dialogue_subgraph = build_dialogue_subgraph().compile()
