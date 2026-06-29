"""装备与属性计算 / Equipment & attribute computation.

纯函数——从属性值 + 装备数据推导战斗数值 / Pure functions for stat derivation.
依赖 src/rules/dnd_rules.py 的 calculate_ac。
"""

from .dnd_rules import calculate_ac


def attr_mod(value: int) -> int:
    """D&D 属性修正 / D&D attribute modifier. (value - 10) // 2."""
    return (value - 10) // 2


def compute_melee_attack(str_val: int, weapon_bonus: int = 0) -> int:
    """近战攻击加值 / Melee attack bonus. 力量修正 + 武器加值."""
    return attr_mod(str_val) + weapon_bonus


def compute_ranged_attack(dex_val: int, weapon_bonus: int = 0) -> int:
    """远程攻击加值 / Ranged attack bonus. 敏捷修正 + 武器加值."""
    return attr_mod(dex_val) + weapon_bonus


def compute_damage_bonus(str_val: int) -> int:
    """力量伤害修正 / Strength damage modifier."""
    return attr_mod(str_val)


def compute_ac(
    base_ac: int = 10,
    dex_val: int = 10,
    armor_type: str = "unarmored",
    shield: bool = False,
) -> int:
    """计算最终 AC / Compute final AC."""
    return calculate_ac(
        base_ac=base_ac,
        dex_mod=attr_mod(dex_val),
        shield_bonus=2 if shield else 0,
        armor_type=armor_type,
    )


def compute_hp(con_val: int, hit_die_value: int = 10) -> int:
    """1级生命值 / Level 1 HP. 生命骰最大值 + 体质修正."""
    return hit_die_value + attr_mod(con_val)
