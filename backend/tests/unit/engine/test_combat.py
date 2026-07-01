"""Combat Engine 单元测试——回合制战斗全流程 / Combat Engine unit tests with full turn-based flow.

per test-driven-development: 先写测试再实现
"""

from unittest.mock import patch

from src.engine.combat.combat_engine import resolve_combat
from src.schemas.request import CombatParticipant, CombatRequest


def _party(name="hero", hp=20, ac=14, atk=5, dmg="1d8+3", dex=2):
    return CombatParticipant(
        name=name,
        team="party",
        hp=hp,
        max_hp=hp,
        ac=ac,
        atk_bonus=atk,
        damage_dice=dmg,
        dex_mod=dex,
    )


def _enemy(name="goblin", hp=7, ac=12, atk=3, dmg="1d6+1", dex=1):
    return CombatParticipant(
        name=name,
        team="enemy",
        hp=hp,
        max_hp=hp,
        ac=ac,
        atk_bonus=atk,
        damage_dice=dmg,
        dex_mod=dex,
    )


class TestCombatBasics:
    def test_empty_participants(self):
        r = resolve_combat(CombatRequest(participants=[]))
        assert r.winner is None
        assert r.rounds == 0

    def test_only_party_wins_immediately(self):
        r = resolve_combat(CombatRequest(participants=[_party("alex")]))
        assert r.winner == "party"

    def test_only_enemy_wins_immediately(self):
        r = resolve_combat(CombatRequest(participants=[_enemy("goblin")]))
        assert r.winner == "enemy"


class TestInitiative:
    def test_higher_dex_goes_first(self):
        alex = _party("alex", dex=4)
        gob = _enemy("goblin", dex=1)
        with (
            patch("src.rules.dnd_rules.roll_d20", return_value=10),
            patch("src.engine.combat.combat_engine_engine.roll_initiative", side_effect=[14, 11]),
        ):
            r = resolve_combat(CombatRequest(participants=[alex, gob]))
            log_names = [e["attacker"] for e in r.combat_log if "attacker" in e]
            assert log_names[0] == "alex"


class TestCombatFlow:
    def test_1v1_party_wins(self):
        hero = _party("hero", hp=20, ac=16, atk=5, dmg="1d8+3")
        gob = _enemy("gob", hp=5, ac=10, atk=2, dmg="1d4")
        with (
            patch("src.rules.dnd_rules.roll_d20", return_value=15),  # 命中
            patch("src.rules.dnd_rules.random.randint", return_value=4),  # 1d8=4
        ):
            r = resolve_combat(CombatRequest(participants=[hero, gob]))
            assert r.winner == "party"
            assert r.rounds >= 1
            assert len(r.survivors) == 1
            assert r.survivors[0]["name"] == "hero"

    def test_high_ac_char_evades(self):
        """高 AC 角色难以被命中，双方可能超时。"""
        hero = _party("hero", hp=10, ac=20, atk=2, dmg="1d4")
        gob = _enemy("gob", hp=10, ac=20, atk=2, dmg="1d4")
        with patch("src.rules.dnd_rules.roll_d20", return_value=5):
            r = resolve_combat(CombatRequest(participants=[hero, gob]))
            # 双方 AC 20, atk=2, roll=5 → 5+2=7 < 20 必定 miss, 战斗超时
            assert r.winner is None

    def test_combat_log_has_details(self):
        hero = _party("hero", hp=10, ac=12, atk=3, dmg="1d6")
        gob = _enemy("gob", hp=3, ac=8, atk=1, dmg="1d4")
        with (
            patch("src.rules.dnd_rules.roll_d20", return_value=18),
            patch("src.rules.dnd_rules.random.randint", return_value=3),
        ):
            r = resolve_combat(CombatRequest(participants=[hero, gob]))
            for entry in r.combat_log:
                assert "attacker" in entry
                assert "target" in entry
                assert "hit" in entry

    def test_critical_hit_in_combat(self):
        hero = _party("hero", hp=20, ac=12, atk=3, dmg="1d6+2")
        gob = _enemy("gob", hp=10, ac=14, atk=1, dmg="1d4")
        with (
            patch("src.rules.dnd_rules.roll_d20", return_value=20),  # 重击！
            patch("src.rules.dnd_rules.random.randint", return_value=3),
        ):
            r = resolve_combat(CombatRequest(participants=[hero, gob]))
            # nat20 hit, damage doubled
            assert r.winner in ("party", "enemy")

    def test_party_wipes(self):
        hero = _party("hero", hp=3, ac=10, atk=1, dmg="1d4")
        gob = _enemy("gob", hp=20, ac=14, atk=5, dmg="2d6+3")
        with (
            patch("src.rules.dnd_rules.roll_d20", return_value=12),
            patch("src.rules.dnd_rules.random.randint", return_value=4),
        ):
            r = resolve_combat(CombatRequest(participants=[hero, gob]))
            assert r.winner == "enemy"
            assert any(s["name"] == "gob" for s in r.survivors)
