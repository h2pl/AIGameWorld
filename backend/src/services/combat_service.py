"""Combat Service: State ↔ Engine adapter.

旧版 resolve_combat 入口已废弃；现在 combat 由 pc_service.act 直接调用
combat_engine.process_combat_action 处理。
此模块保留为兼容入口，仅做简单委托。
"""

from ..engine.combat import combat_engine
from ..graph.state import EngineSubState
from ..schemas.request import CombatParticipant
from ..utils.logging import get_logger


async def combat(state: EngineSubState) -> dict:
    """Phase 4: 战斗裁决 / Combat resolution."""
    get_logger(__name__).info("[service]")
    raw = state.get("participants", [])
    if raw and isinstance(raw[0], str):
        # 旧格式兼容：["hero", "goblin"] → 默认 party/enemy
        participants = [
            CombatParticipant(name=p, team="party" if i == 0 else "enemy")
            for i, p in enumerate(raw)
        ]
    else:
        participants = raw

    if len(participants) < 2:
        return {"engine_results": [], "combat_result": {}}

    pc_id = participants[0].name
    target_id = participants[1].name
    decision = {
        "type": "combat",
        "pc_id": pc_id,
        "target_id": target_id,
        "target_type": "actor",
    }
    result = await combat_engine.process_combat_action(
        decision=decision,
        pcs={},
        actors={},
        tick=state.get("round", 1),
    )
    result_dict = result.model_dump() if result else {}
    return {
        "engine_results": [{"engine": "combat", "result": result_dict}],
        "combat_result": result_dict,
    }
