"""Quest Engine Subgraph / 任务引擎子图."""
from langgraph.graph import StateGraph, END
from ...engine.quest.quest import QuestSubState, check_quests_node

def build_quest_subgraph() -> StateGraph:
    graph = StateGraph(QuestSubState)
    graph.add_node("quest_update", check_quests_node)
    graph.set_entry_point("quest_update")
    graph.add_edge("quest_update", END)
    return graph

quest_subgraph = build_quest_subgraph().compile()
