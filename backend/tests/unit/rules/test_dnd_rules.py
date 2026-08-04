"""D20 规则库 单元测试——纯函数全覆盖 / D20 Rules unit tests with full coverage.

per test-driven-development: 先写测试再实现
per python-testing-patterns: 属性测试(1000次) + mock 骰子 + 边界条件
"""

from unittest.mock import patch

from src.rules.dnd_rules import (
    AttackResult,
    CheckResult,
    attack_roll,
    calculate_ac,
    resolve_check,
    roll_d20,
    roll_damage,
    roll_initiative,
    saving_throw,
    with_advantage,
    with_disadvantage,
)

# ── roll_d20 / 基础掷骰 ──


class TestRollD20:
    def test_roll_range(self):
        """1000 次掷骰全在 1-20 范围 / 1000 rolls all in 1-20."""
        for _ in range(1000):
            r = roll_d20()
            assert 1 <= r <= 20

    def test_critical_nat20(self):
        with patch("src.rules.dnd_rules.random.randint", return_value=20):
            assert roll_d20() == 20

    def test_critical_nat1(self):
        with patch("src.rules.dnd_rules.random.randint", return_value=1):
            assert roll_d20() == 1


# ── 优劣势 / Advantage & Disadvantage ──


class TestAdvantage:
    def test_advantage_takes_higher(self):
        call_count = 0

        def mock_randint(a, b):
            nonlocal call_count
            call_count += 1
            return [7, 15][call_count - 1]

        with patch("src.rules.dnd_rules.random.randint", side_effect=mock_randint):
            assert with_advantage() == 15

    def test_disadvantage_takes_lower(self):
        call_count = 0

        def mock_randint(a, b):
            nonlocal call_count
            call_count += 1
            return [14, 3][call_count - 1]

        with patch("src.rules.dnd_rules.random.randint", side_effect=mock_randint):
            assert with_disadvantage() == 3


# ── resolve_check / D20 检定 ──


class TestResolveCheck:
    def test_pass(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=10):
            r = resolve_check(bonus=5, dc=15)
            assert r.success is True
            assert r.total == 15
            assert isinstance(r, CheckResult)

    def test_fail(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=3):
            r = resolve_check(bonus=2, dc=15)
            assert r.success is False
            assert r.total == 5

    def test_exact_match_passes(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=15):
            r = resolve_check(bonus=0, dc=15)
            assert r.success is True

    def test_nat20_always_passes(self):
        """nat20 无论 DC 多高必定成功."""
        with patch("src.rules.dnd_rules.roll_d20", return_value=20):
            r = resolve_check(bonus=-5, dc=30)
            assert r.success is True
            assert r.is_critical is True

    def test_nat1_always_fails(self):
        """nat1 无论 DC 多低必定失败."""
        with patch("src.rules.dnd_rules.roll_d20", return_value=1):
            r = resolve_check(bonus=10, dc=5)
            assert r.success is False
            assert r.is_fumble is True

    def test_negative_bonus(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=10):
            r = resolve_check(bonus=-3, dc=10)
            assert r.success is False
            assert r.total == 7


# ── attack_roll / 攻击检定 ──


class TestAttackRoll:
    def test_hit_normal(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=12):
            r = attack_roll(atk_bonus=5, target_ac=15, damage_dice="1d8")
            assert r.success is True
            assert isinstance(r, AttackResult)

    def test_miss(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=3):
            r = attack_roll(atk_bonus=2, target_ac=15, damage_dice="1d6")
            assert r.success is False
            assert r.damage == 0

    def test_critical_hit(self):
        """nat20 重击——必定命中 + 伤害骰翻倍."""
        with (
            patch("src.rules.dnd_rules.roll_d20", return_value=20),
            patch("src.rules.dnd_rules.random.randint", return_value=4),
        ):
            r = attack_roll(atk_bonus=0, target_ac=25, damage_dice="2d6+3")
            assert r.success is True
            assert r.is_critical is True
            assert r.damage > 0  # 2d6+3 重击=4d6+3

    def test_nat1_auto_miss(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=1):
            r = attack_roll(atk_bonus=10, target_ac=5, damage_dice="1d8")
            assert r.success is False
            assert r.is_fumble is True
            assert r.damage == 0

    def test_attack_damage_positive(self):
        with (
            patch("src.rules.dnd_rules.roll_d20", return_value=15),
            patch("src.rules.dnd_rules.random.randint", return_value=3),
        ):
            r = attack_roll(atk_bonus=2, target_ac=15, damage_dice="1d8")
            assert r.damage == 3


# ── damage_roll / 伤害骰 ──


class TestRollDamage:
    def test_single_die(self):
        with patch("src.rules.dnd_rules.random.randint", return_value=4):
            assert roll_damage("1d8") == 4

    def test_multiple_dice(self):
        with patch("src.rules.dnd_rules.random.randint", return_value=3):
            assert roll_damage("2d6") == 6

    def test_dice_with_plus(self):
        with patch("src.rules.dnd_rules.random.randint", return_value=5):
            assert roll_damage("1d8+3") == 8

    def test_dice_with_spaces(self):
        with patch("src.rules.dnd_rules.random.randint", return_value=2):
            assert roll_damage("2d10 + 5") == 9

    def test_large_damage(self):
        with patch("src.rules.dnd_rules.random.randint", return_value=6):
            assert roll_damage("4d6") == 24

    def test_damage_never_negative(self):
        """伤害有 floor 保护 / Damage has floor protection."""
        with patch("src.rules.dnd_rules.random.randint", return_value=1):
            assert roll_damage("1d6+0") >= 0


# ── initiative / 先攻 ──


class TestInitiative:
    def test_initiative_formula(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=10):
            assert roll_initiative(dex_mod=3) == 13

    def test_negative_dex(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=10):
            assert roll_initiative(dex_mod=-2) == 8


# ── saving_throw / 豁免 ──


class TestSavingThrow:
    def test_pass_with_proficiency(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=12):
            r = saving_throw(attr_mod=2, proficiency_bonus=2, dc=15)
            assert r.success is True
            assert r.total == 16

    def test_fail(self):
        with patch("src.rules.dnd_rules.roll_d20", return_value=8):
            r = saving_throw(attr_mod=1, dc=15)
            assert r.success is False


# ── AC 计算 / Armor Class ──


class TestCalculateAC:
    def test_unarmored_no_shield(self):
        assert calculate_ac(10, 2, armor_type="unarmored") == 12

    def test_with_shield(self):
        assert calculate_ac(10, 2, 2, armor_type="light") == 14

    def test_medium_armor_dex_cap(self):
        """中甲敏捷修正上限 +2."""
        assert calculate_ac(14, 4, armor_type="medium") == 16  # 14 + min(4,2)
        assert calculate_ac(14, 1, armor_type="medium") == 15  # 14 + min(1,2)

    def test_heavy_armor_no_dex(self):
        """重甲敏捷不参与."""
        assert calculate_ac(18, 3, armor_type="heavy") == 18
        assert calculate_ac(18, -1, armor_type="heavy") == 18

    def test_negative_dex_mod(self):
        assert calculate_ac(12, -1, armor_type="light") == 11

    def test_unarmored(self):
        assert calculate_ac(10, 3, armor_type="unarmored") == 13
