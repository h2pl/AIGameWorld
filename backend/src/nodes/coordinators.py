"""Coordinator Nodes: Phase 3/4/7 — 协调多个子 Node。

每个 coordinator 是一个纯函数：读 State、调其他 node、合并结果、写 State。
不是 subgraph — 不含 StateGraph.compile()。
"""

from typing import Any

from .character_nodes import pc_decide_node, actor_decide_node
from .combat_nodes import combat_node
from .dialogue_nodes import dialogue_node
from .exploration_nodes import exploration_node
from .quest_nodes import quest_node
from .reflection_nodes import reflection_node
from .summarizer_nodes import summarizer_node


def phase3_character_decide(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 3: 唤醒 DM 指定的 PC + Actor 决策。

    后续 M5 改为 Send fan-out 并行 / Future M5: Send fan-out.
    """
    direction = state.get("scene_direction", {})
    featured_pcs = direction.get("featured_pcs", [])
    featured_actors = direction.get("featured_actors", [])
    plot_brief = state.get("plot_brief", "")

    actions = []

    for pc_id in featured_pcs:
        result = pc_decide_node({"pc_id": pc_id, "plot_brief": plot_brief})
        if result.get("action_out"):
            actions.append(result["action_out"])

    for actor_id in featured_actors:
        result = actor_decide_node({"actor_id": actor_id, "plot_brief": plot_brief})
        if result.get("action_out"):
            actions.append(result["action_out"])

    return {"character_actions": actions}


def phase4_engine_router(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 4: 条件路由到各 Engine。

    后续 M6 按 Action type 条件路由 / Future M6: conditional routing.
    """
    results = []

    cr = combat_node({"participants": [], "round": 1})
    results.append({"engine": "combat", "result": cr.get("result")})

    dr = dialogue_node({"speaker": "", "target": "", "intent": ""})
    results.append({"engine": "dialogue", "result": dr.get("check_result")})

    er = exploration_node({"character_id": "", "action_type": ""})
    results.append({"engine": "exploration", "result": er.get("check_result")})

    qr = quest_node({"quests": [], "event_log": []})
    results.append({"engine": "quest", "completed": qr.get("completed_quests", [])})

    return {"engine_results": results, "combat_result": cr.get("result")}


def phase7_reflection_coordinator(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 7: Reflection + Summarizer 协调。"""
    reflection_node({"character_id": "", "memories": []})
    summarizer_node({"events": [], "tick": state.get("tick", 0)})
    return {"reflected_characters": [], "summary_compressed": False}
