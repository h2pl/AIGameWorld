"""Phase 4 节点: 路由到各 Engine。"""
from typing import Any

from .combat_node import combat_node
from .dialogue_node import dialogue_node
from .exploration_node import exploration_node
from .quest_node import quest_node


def engine_route_node(state: dict[str, Any]) -> dict[str, Any]:
    """条件路由到各 Engine。后续 M6 按 Action type 条件路由。"""
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
