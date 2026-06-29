"""DndRules: D20 核心规则库 / D20 Core Rules Library.
共享 Python 模块（非子图），纯函数 / Shared module (not a subgraph), pure functions.
各 Engine 引用此模块做确定性裁决 / All engines import this module for deterministic resolution.

Mock: 空实现，后续 M6 补充 SRD 5.1/5.2 规则 / Mock: empty, M6 fills SRD 5.1/5.2 rules.
"""

import random
from typing import Any


def roll_d20() -> int:
    """掷 D20 / Roll a d20.

    Returns:
        int: 1-20 的随机数 / Random number 1-20
    """
    return random.randint(1, 20)


def resolve_check(bonus: int, dc: int) -> dict[str, Any]:
    """D20 检定（d20 + bonus vs DC）/ D20 check (d20 + bonus vs DC).

    Args:
        bonus: 加值（属性修正+熟练）/ Bonus (ability mod + proficiency)
        dc: 难度等级 / Difficulty Class

    Returns:
        dict: {success: bool, roll: int, total: int}
    """
    roll = roll_d20()
    total = roll + bonus
    return {"success": total >= dc, "roll": roll, "bonus": bonus, "dc": dc, "total": total}


def roll_damage(dice_str: str) -> int:
    """掷伤害骰 / Roll damage dice.

    Args:
        dice_str: 骰子描述如 "1d8" 或 "2d6+3" / Dice description e.g. "1d8" or "2d6+3"

    Returns:
        int: 总伤害 / Total damage
    """
    # Mock: 简单解析 / Mock: simple parse
    if "+" in dice_str:
        dice_part, plus = dice_str.split("+")
        plus = int(plus.strip())
    else:
        dice_part = dice_str
        plus = 0
    count, sides = dice_part.split("d")
    total = sum(random.randint(1, int(sides)) for _ in range(int(count)))
    return total + plus


def calculate_ac(base_ac: int, dex_mod: int, shield_bonus: int = 0) -> int:
    """计算护甲等级 / Calculate Armor Class.

    Args:
        base_ac: 护甲基础 AC（或 10 如无护甲）/ Base armor AC (or 10 if none)
        dex_mod: 敏捷修正 / Dexterity modifier
        shield_bonus: 盾牌加值 / Shield bonus

    Returns:
        int: 最终 AC / Final AC
    """
    return base_ac + dex_mod + shield_bonus
