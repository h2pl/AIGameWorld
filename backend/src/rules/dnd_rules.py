"""D20 核心规则库 / D20 Core Rules Library.

纯数值函数，零外部依赖 / Pure numeric functions, zero external deps.
Engine 层引用做确定性裁决 / Engines import this for deterministic resolution.

基于 SRD 5.1 / Based on SRD 5.1.
"""

import random
from dataclasses import dataclass

# ── 数据类型 / Data types ──


@dataclass
class CheckResult:
    """D20 检定结果 / D20 check result."""

    success: bool
    roll: int
    bonus: int
    dc: int
    total: int
    is_critical: bool = False  # nat20
    is_fumble: bool = False  # nat1


@dataclass
class AttackResult(CheckResult):
    """攻击检定结果 / Attack roll result."""

    damage: int = 0
    damage_dice: str = ""


# ── 骰子函数 / Dice functions ──


def roll_d20() -> int:
    """掷 D20 / Roll a d20. 返回 1-20."""
    return random.randint(1, 20)


def with_advantage() -> int:
    """优势掷骰：掷两个 d20 取高 / Roll 2d20 take highest."""
    return max(roll_d20(), roll_d20())


def with_disadvantage() -> int:
    """劣势掷骰：掷两个 d20 取低 / Roll 2d20 take lowest."""
    return min(roll_d20(), roll_d20())


def roll_damage(dice_str: str) -> int:
    """掷伤害骰 / Roll damage dice.

    Args:
        dice_str: "1d8", "2d6+3", "1d8 + 3" 等

    Returns:
        总伤害（最小 0）
    """
    dice_str = dice_str.replace(" ", "")
    if "+" in dice_str:
        dice_part, mod = dice_str.split("+")
        mod = int(mod)
    else:
        dice_part, mod = dice_str, 0

    count, sides = dice_part.split("d")
    total = sum(random.randint(1, int(sides)) for _ in range(int(count))) + mod
    return max(total, 0)


# ── 属性修正值 / Ability modifiers ──


def ability_modifier(score: int) -> int:
    """属性值 → D&D 修正值 / Ability score → D&D modifier. (score - 10) // 2."""
    return (score - 10) // 2


# ── 检定函数 / Check functions ──


def resolve_check(bonus: int, dc: int) -> CheckResult:
    """D20 检定：1d20 + bonus vs DC / D20 check."""
    roll = roll_d20()
    total = roll + bonus
    return CheckResult(
        success=(total >= dc or roll == 20) and roll != 1,
        roll=roll,
        bonus=bonus,
        dc=dc,
        total=total,
        is_critical=(roll == 20),
        is_fumble=(roll == 1),
    )


def attack_roll(atk_bonus: int, target_ac: int, damage_dice: str = "1d6") -> AttackResult:
    """攻击检定 / Attack roll.

    nat20: 必定命中 + 重击（伤害骰翻倍）
    nat1: 必定失手
    """
    roll = roll_d20()
    total = roll + atk_bonus
    hit = (total >= target_ac or roll == 20) and roll != 1

    damage = 0
    if hit:
        if roll == 20:
            doubled = _double_dice(damage_dice)
            damage = roll_damage(doubled)
        else:
            damage = roll_damage(damage_dice)

    return AttackResult(
        success=hit,
        roll=roll,
        bonus=atk_bonus,
        dc=target_ac,
        total=total,
        is_critical=(roll == 20),
        is_fumble=(roll == 1),
        damage=damage,
        damage_dice=damage_dice,
    )


def _double_dice(dice_str: str) -> str:
    """翻倍伤害骰数量 / Double the number of damage dice.
    "2d6+3" → "4d6+3", "1d8" → "2d8"
    """
    s = dice_str.replace(" ", "")
    if "+" in s:
        dice, mod = s.rsplit("+", 1)
        count, sides = dice.split("d")
        return f"{int(count) * 2}d{sides}+{mod}"
    count, sides = s.split("d")
    return f"{int(count) * 2}d{sides}"


def roll_initiative(dex_mod: int) -> int:
    """先攻掷骰 / Initiative roll. 1d20 + 敏捷修正."""
    return roll_d20() + dex_mod


def saving_throw(attr_mod: int, proficiency_bonus: int = 0, dc: int = 10) -> CheckResult:
    """豁免检定 / Saving throw. 1d20 + 属性修正 + 熟练加值 vs DC."""
    return resolve_check(bonus=attr_mod + proficiency_bonus, dc=dc)


# ── 护甲 / Armor Class ──

_AC_DEX_CAP: dict[str, int | None] = {
    "unarmored": None,  # 无限制，负敏捷也会降 AC
    "light": None,  # 全额敏捷
    "medium": 2,  # 敏捷最多 +2
    "heavy": 0,  # 敏捷不参与（不会降 AC）
}


def calculate_ac(
    base_ac: int, dex_mod: int, shield_bonus: int = 0, armor_type: str = "light"
) -> int:
    """计算护甲等级 / Calculate Armor Class."""
    cap = _AC_DEX_CAP.get(armor_type)
    if cap is not None:
        dex_mod = min(dex_mod, cap)
    if armor_type == "heavy":
        dex_mod = max(dex_mod, 0)
    return base_ac + dex_mod + shield_bonus
