"""Combat Node: State <-> Service glue / 战斗节点：State ↔ Service 胶水。"""
from typing import Any
from ..engine.combat.combat import resolve_combat


def combat_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 4: 战斗裁决 / Combat resolution.

    产出 / Outputs: result
    """
    result = resolve_combat(
        participants=state.get("participants", []),
        round=state.get("round", 1),
    )
    return {"result": result}
