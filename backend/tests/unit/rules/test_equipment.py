"""Equipment 规则 单元测试——属性修正+AC+攻击+伤害 / Equipment rules unit tests.

per test-driven-development + python-testing-patterns.
"""

from src.rules.equipment import (
    attr_mod,
    compute_ac,
    compute_damage_bonus,
    compute_hp,
    compute_melee_attack,
    compute_ranged_attack,
)


class TestAttrMod:
    """D&D 属性修正 / Attribute modifier."""

    def test_average(self):
        assert attr_mod(10) == 0
        assert attr_mod(11) == 0

    def test_positive(self):
        assert attr_mod(12) == 1
        assert attr_mod(14) == 2
        assert attr_mod(18) == 4
        assert attr_mod(20) == 5

    def test_negative(self):
        assert attr_mod(9) == -1
        assert attr_mod(8) == -1
        assert attr_mod(6) == -2
        assert attr_mod(3) == -4


class TestMeleeAttack:
    """近战攻击加值 / Melee attack."""

    def test_str_only(self):
        assert compute_melee_attack(16) == 3  # +3 from strength

    def test_with_weapon_bonus(self):
        assert compute_melee_attack(14, weapon_bonus=1) == 3  # +2+1

    def test_negative_str(self):
        assert compute_melee_attack(8) == -1


class TestRangedAttack:
    """远程攻击 / Ranged attack."""

    def test_dex_based(self):
        assert compute_ranged_attack(18) == 4


class TestDamageBonus:
    """伤害修正 / Damage bonus."""

    def test_positive_str(self):
        assert compute_damage_bonus(16) == 3

    def test_negative_str(self):
        assert compute_damage_bonus(6) == -2


class TestComputeAC:
    """AC 计算 / AC computation."""

    def test_unarmored(self):
        assert compute_ac(base_ac=10, dex_val=16, armor_type="unarmored") == 13

    def test_medium_armor(self):
        assert compute_ac(base_ac=14, dex_val=18, armor_type="medium") == 16  # 14+2(capped)

    def test_heavy_armor(self):
        assert compute_ac(base_ac=18, dex_val=20, armor_type="heavy") == 18  # dex 不参与

    def test_heavy_armor_negative_dex(self):
        assert compute_ac(base_ac=18, dex_val=6, armor_type="heavy") == 18  # 负敏捷不降

    def test_with_shield(self):
        assert compute_ac(base_ac=14, dex_val=14, armor_type="medium", shield=True) == 18  # 14+2+2


class TestHP:
    """生命值 / HP."""

    def test_fighter_hp(self):
        assert compute_hp(con_val=14, hit_die_value=10) == 12  # 10+2

    def test_wizard_hp(self):
        assert compute_hp(con_val=10, hit_die_value=6) == 6  # 6+0

    def test_frail_hp(self):
        assert compute_hp(con_val=6, hit_die_value=8) == 6  # 8-2
