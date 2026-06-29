"""Combat Engine——回合制战斗裁决 / Turn-based combat resolution.

依赖 src/rules/dnd_rules.py 做 D20 判定。
"""

import random

from ...rules.dnd_rules import attack_roll, roll_initiative
from ...schemas.request import CombatRequest
from ...schemas.response import CombatResponse

_MAX_ROUNDS = 20


def resolve_combat(req: CombatRequest) -> CombatResponse:
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
            targets = [
                p for p in order
                if p.team != attacker.team and p.hp > 0
            ]
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
            return CombatResponse(winner="party", rounds=rounds, survivors=survivors, combat_log=combat_log)
        if not party_alive:
            survivors = [p.model_dump() for p in order if p.hp > 0]
            return CombatResponse(winner="enemy", rounds=rounds, survivors=survivors, combat_log=combat_log)

    # 超时 / Timeout
    survivors = [p.model_dump() for p in order if p.hp > 0]
    return CombatResponse(winner=None, rounds=rounds, survivors=survivors, combat_log=combat_log,
                          errors=["战斗达到最大回合数，强制结束 / Combat reached max rounds, forced end"])
