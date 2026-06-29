"""Phase 4 子图——按 action_type 路由到对应 Engine / Route to matching engine by action type.

entry → route_engine → [combat | dialogue | exploration | quest] → END
"""

from langgraph.graph import END, StateGraph

from ...services import combat_service, dialogue_service, exploration_service, quest_service
from ..state import EngineSubState

_ROUTES: dict[str, str | None] = {
    "attack": "combat_service.combat",
    "talk": None,  # 普通对话无需检定 / ordinary chat needs no check
    "persuade": "dialogue_service.dialogue",
    "intimidate": "dialogue_service.dialogue",
    "deceive": "dialogue_service.dialogue",
    "search": "exploration_service.exploration",
    "perception": "exploration_service.exploration",
    "pick_lock": "exploration_service.exploration",
    "disarm_trap": "exploration_service.exploration",
    "break_door": "exploration_service.exploration",
    "quest": "quest_service.quest",
}


def route_engine(state: EngineSubState) -> str:
    """按 action_type 路由 / Route by action type."""
    action = state.get("action_type", "")
    target = _ROUTES.get(action)
    return target if target else END


def build_engine_subgraph() -> StateGraph:
    graph = StateGraph(EngineSubState)
    graph.add_node("combat_service.combat", combat_service.combat)
    graph.add_node("dialogue_service.dialogue", dialogue_service.dialogue)
    graph.add_node("exploration_service.exploration", exploration_service.exploration)
    graph.add_node("quest_service.quest", quest_service.quest)
    graph.add_node("route_engine", lambda s: {})
    graph.set_entry_point("route_engine")
    graph.add_conditional_edges(
        "route_engine",
        route_engine,
        {
            "combat_service.combat": "combat_service.combat",
            "dialogue_service.dialogue": "dialogue_service.dialogue",
            "exploration_service.exploration": "exploration_service.exploration",
            "quest_service.quest": "quest_service.quest",
            END: END,
        },
    )
    for node in [
        "combat_service.combat",
        "dialogue_service.dialogue",
        "exploration_service.exploration",
        "quest_service.quest",
    ]:
        graph.add_edge(node, END)
    return graph


engine_subgraph = build_engine_subgraph().compile()
