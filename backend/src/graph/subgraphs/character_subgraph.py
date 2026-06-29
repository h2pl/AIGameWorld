"""Phase 3 子图: Send() fan-out 并行角色决策。

pass_through ──→ [conditional: dispatch_characters → Send × N] ──→ character_agent（并行）
                                                                          ↓
                                                                   character_actions (add 合并)
"""

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from ...services import character_service
from ..state import OverallState


def _pass_through(state: OverallState) -> dict:
    """入站节点：不做任何转换，直接透传 / Pass-through entry node."""
    return {}


def dispatch_characters(state: OverallState) -> list[Send]:
    """P3-3: 并行唤醒 DM 指定的 PC 和 Actor."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    sends: list[Send] = []

    for pc_id in direction.get("featured_pcs", []):
        sends.append(Send("character_agent", {
            "character_id": pc_id,
            "character_type": "pc",
            "plot_brief": plot_brief,
            "tick": tick,
        }))

    for actor_id in direction.get("featured_actors", []):
        sends.append(Send("character_agent", {
            "character_id": actor_id,
            "character_type": "actor",
            "plot_brief": plot_brief,
            "tick": tick,
        }))

    return sends


def build_character_subgraph() -> StateGraph:
    graph = StateGraph(OverallState)
    graph.add_node("pass_through", _pass_through)
    graph.add_node("character_agent", character_service.character_agent)
    graph.set_entry_point("pass_through")
    graph.add_conditional_edges("pass_through", dispatch_characters)
    graph.add_edge("character_agent", END)
    return graph


character_subgraph = build_character_subgraph().compile()
