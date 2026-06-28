"""Phase 4 Service: 路由到各 Engine 协调。"""
from typing import Any

from .combat_service import combat
from .dialogue_service import dialogue
from .exploration_service import exploration
from .quest_service import quest


def engine_route(state: dict[str, Any]) -> dict[str, Any]:
    """条件路由到各 Engine。后续 M6 按 Action type 条件路由。"""
    results = []

    cr = combat({"participants": [], "round": 1})
    results.append({"engine": "combat", "result": cr.get("result")})

    dr = dialogue({"speaker": "", "target": "", "intent": ""})
    results.append({"engine": "dialogue", "result": dr.get("check_result")})

    er = exploration({"character_id": "", "action_type": ""})
    results.append({"engine": "exploration", "result": er.get("check_result")})

    qr = quest({"quests": [], "event_log": []})
    results.append({"engine": "quest", "completed": qr.get("completed_quests", [])})

    return {"engine_results": results, "combat_result": cr.get("result")}
