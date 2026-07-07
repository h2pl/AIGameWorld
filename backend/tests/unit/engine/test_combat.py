"""Combat Engine 单元测试——纯 LLM 驱动战斗 / Combat engine tests for LLM-driven combat."""

from unittest.mock import AsyncMock

import pytest

from src.domain import Memory
from src.domain.actor import Actor
from src.domain.player_character import PlayerCharacter
from src.engine.combat.combat_engine import process_combat_action
from src.schemas.llm_output import CombatNarrationSchema


def _pc(
    pc_id: str = "pc1",
    name: str = "英雄",
    position_x: int = 0,
    position_y: int = 0,
    hp: int = 20,
    ac: int = 14,
    attack_bonus: int = 5,
    damage_dice: str = "1d8+3",
) -> PlayerCharacter:
    return PlayerCharacter(
        id=pc_id,
        name=name,
        position_x=position_x,
        position_y=position_y,
        combat_json=f'{{"hp":{hp},"max_hp":{hp},"ac":{ac},"attack_bonus":{attack_bonus},"damage_dice":"{damage_dice}"}}',
        attributes_json='{"strength":14,"dexterity":12}',
    )


def _actor(
    actor_id: str = "goblin",
    name: str = "地精",
    position_x: int = 5,
    position_y: int = 5,
    hp: int = 7,
    ac: int = 12,
    attack_bonus: int = 3,
    damage_dice: str = "1d6+1",
) -> Actor:
    return Actor(
        id=actor_id,
        name=name,
        position_x=position_x,
        position_y=position_y,
        combat_json=f'{{"hp":{hp},"max_hp":{hp},"ac":{ac},"attack_bonus":{attack_bonus},"damage_dice":"{damage_dice}"}}',
        attributes_json='{"strength":10,"dexterity":10}',
    )


class TestCombatAction:
    """process_combat_action 单动作执行测试 / Single-action combat execution tests."""

    @pytest.mark.asyncio
    async def test_non_combat_action_skipped(self):
        event = await process_combat_action(
            decision={"type": "talk", "pc_id": "pc1", "target_id": "npc1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_combat_without_target_skipped(self):
        event = await process_combat_action(
            decision={"type": "combat", "pc_id": "pc1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_combat_moves_pc_adjacent_to_actor(self):
        """combat 将 PC 移动到目标 Actor 旁边 / Combat moves PC adjacent to target actor."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CombatNarrationSchema(narration="他一剑劈向地精。")
        )
        pcs = {"pc1": _pc(position_x=0, position_y=0)}
        actors = {"goblin": _actor(position_x=5, position_y=5)}
        event = await process_combat_action(
            decision={
                "type": "combat",
                "pc_id": "pc1",
                "target_id": "goblin",
                "target_type": "actor",
            },
            scene={"id": "forest", "name": "森林", "type": "wilderness"},
            pcs=pcs,
            actors=actors,
            tick=1,
            config={"configurable": {"llm": llm}},
        )
        assert event is not None
        assert event.kind == "pc_combat"
        assert event.target_id == "goblin"
        assert len(event.waypoints) == 2
        final = event.waypoints[-1]
        assert abs(final["x"] - 5) <= 1 and abs(final["y"] - 5) <= 1
        assert pcs["pc1"].position_x == final["x"]
        assert pcs["pc1"].position_y == final["y"]

    @pytest.mark.asyncio
    async def test_combat_defeats_target(self):
        """LLM 判定目标被击败时更新目标状态 / LLM defeat updates target state."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CombatNarrationSchema(
                narration="他一剑刺穿地精的胸膛，地精倒地不起。",
                target_defeated=True,
                result="地精被击败",
            )
        )
        pcs = {"pc1": _pc(position_x=4, position_y=5)}
        actors = {"goblin": _actor(position_x=5, position_y=5)}
        event = await process_combat_action(
            decision={
                "type": "combat",
                "pc_id": "pc1",
                "target_id": "goblin",
                "target_type": "actor",
            },
            scene={"id": "forest", "name": "森林", "type": "wilderness"},
            pcs=pcs,
            actors=actors,
            tick=2,
            config={"configurable": {"llm": llm}},
        )
        assert event.target_defeated is True
        assert event.winner == "party"
        assert actors["goblin"].status == "dead"
        assert actors["goblin"].combat_json.count('"hp"') == 1
        assert '"hp": 0' in actors["goblin"].combat_json or '"hp":0' in actors["goblin"].combat_json

    @pytest.mark.asyncio
    async def test_combat_stores_memory(self):
        """combat 结果写入 pc_memory_map / Combat result is staged into state memory map."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CombatNarrationSchema(narration="他击中了敌人。")
        )
        pc_memory_map: dict[str, list[Memory]] = {}
        pcs = {"pc1": _pc(position_x=4, position_y=5)}
        actors = {"goblin": _actor(position_x=5, position_y=5)}
        await process_combat_action(
            decision={
                "type": "combat",
                "pc_id": "pc1",
                "target_id": "goblin",
                "target_type": "actor",
            },
            scene={"id": "forest", "name": "森林", "type": "wilderness"},
            pcs=pcs,
            actors=actors,
            tick=3,
            pc_memory_map=pc_memory_map,
            config={"configurable": {"llm": llm}},
        )
        assert len(pc_memory_map.get("pc1", [])) == 1
        mem = pc_memory_map["pc1"][0]
        assert mem.memory_type == "combat"
        assert mem.tick == 3
