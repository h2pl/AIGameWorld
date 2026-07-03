"""Combat Engine——回合制战斗裁决 / Turn-based combat resolution.

依赖 src/rules/dnd_rules.py 做 D20 判定。
"""

import logging
import random

from langchain_core.runnables.config import RunnableConfig

from ...rules.dnd_rules import attack_roll, roll_initiative
from ...schemas.request import CombatRequest
from ...schemas.response import CombatResponse

logger = logging.getLogger("aw.eng.combat")
_MAX_ROUNDS = 20


def resolve_combat(req: CombatRequest) -> CombatResponse:
    logging.getLogger("aw.eng").info("[combat]")
    """战斗裁决主入口 / Combat resolution entry point."""
    participants = [p.model_copy() for p in req.participants]
    if not participants:
        return CombatResponse()

    party = [p for p in participants if p.team == "party"]
    enemy = [p for p in participants if p.team == "enemy"]
    if not party:
        return CombatResponse(winner="enemy", survivors=[p.model_dump() for p in enemy])
    if not enemy:
        return CombatResponse(winner="party", survivors=[p.model_dump() for p in party])

    # 1. 先攻排序 / Initiative
    order = sorted(participants, key=lambda p: roll_initiative(p.dex_mod), reverse=True)

    combat_log: list[dict] = []
    rounds = 0

    # 2. 回合循环 / Round loop
    for rnd in range(1, _MAX_ROUNDS + 1):
        rounds = rnd

        for attacker in order:
            if attacker.hp <= 0:
                continue

            # 找活着的对方
            targets = [p for p in order if p.team != attacker.team and p.hp > 0]
            if not targets:
                break
            target = random.choice(targets)

            # 攻击判定 / Attack roll
            result = attack_roll(attacker.atk_bonus, target.ac, attacker.damage_dice)
            turn = {
                "attacker": attacker.name,
                "target": target.name,
                "hit": result.success,
                "roll": result.roll,
                "total": result.total,
                "ac": target.ac,
                "damage": result.damage,
                "critical": result.is_critical,
                "fumble": result.is_fumble,
                "target_hp_before": target.hp,
            }
            if result.success:
                target.hp = max(target.hp - result.damage, 0)
                turn["target_hp_after"] = target.hp
                if target.hp <= 0:
                    turn["killed"] = True
            else:
                turn["target_hp_after"] = target.hp

            combat_log.append(turn)

        # 检查是否有一方全灭 / Check wipe
        party_alive = any(p for p in order if p.team == "party" and p.hp > 0)
        enemy_alive = any(p for p in order if p.team == "enemy" and p.hp > 0)

        if not enemy_alive:
            survivors = [p.model_dump() for p in order if p.hp > 0]
            return CombatResponse(
                winner="party", rounds=rounds, survivors=survivors, combat_log=combat_log
            )
        if not party_alive:
            survivors = [p.model_dump() for p in order if p.hp > 0]
            return CombatResponse(
                winner="enemy", rounds=rounds, survivors=survivors, combat_log=combat_log
            )

    # 超时 / Timeout
    survivors = [p.model_dump() for p in order if p.hp > 0]
    return CombatResponse(
        winner=None,
        rounds=rounds,
        survivors=survivors,
        combat_log=combat_log,
        errors=["战斗达到最大回合数，强制结束 / Combat reached max rounds, forced end"],
    )


# TODO: combat 尚未接入完整战斗结算——PC/敌人的战斗属性（hp/ac/atk_bonus 等）
# 目前不在 decide 阶段可用，暂时只记录战斗意图，不调用 resolve_combat。
# TODO: full combat resolution not wired yet — PC/enemy combat stats (hp/ac/
# atk_bonus etc.) are not available at the decide stage, so this only records
# the combat intent as an event without calling resolve_combat.
async def process_combat_action(decision: dict, config: RunnableConfig = None) -> dict | None:
    """处理单个 combat 决策 → 记录战斗意图（尚未结算），返回原始结果（不构造事件）/
    Record a combat intent (not resolved yet), return the raw result (not an event)."""
    if decision.get("type") != "combat":
        return None
    target_id = decision.get("target_id", "")
    if not target_id:
        return None

    char_id = decision.get("pc_id", "")
    description = decision.get("description", "")
    logger.info("[combat] %s → %s（意图记录，未结算）", char_id, target_id)
    return {
        "kind": "pc_combat",
        "pc_id": char_id,
        "target_id": target_id,
        "description": description,
        "resolved": False,
    }
