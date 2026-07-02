"""Services 测试——对齐当前 graph/service/engine 结构。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.response import SceneObservation
from src.services import (
    character_service,
    dm_service,
    message_service,
    reflection_service,
    scene_service,
)


def _overall_state(**overrides):
    """构造当前 OverallState 最小输入 / Build minimal OverallState input."""
    return {
        "tick": 0,
        "world_id": "world-1",
        "tick_message_id": "tick-msg-1",
        "scene_observations": [],
        "hints": [],
        "plot_brief": "",
        "scene_id": "scene-1",
        "character_actions": [],
        "narrative": "",
        "reflected_characters": [],
        "summary_compressed": False,
        "errors": [],
        "needs_reflection": False,
        **overrides,
    }


def _char_repo_config(pcs: list) -> dict:
    """构造带 char_repo 的 config / Build config with a char repo mock."""
    char_repo = AsyncMock()
    char_repo.load_pcs = AsyncMock(return_value=pcs)
    return {"configurable": {"repos": {"char": char_repo}}}


class TestCharacterService:
    """角色服务测试 / Character service tests."""

    @pytest.mark.asyncio
    async def test_observe_scene_returns_scene_observations(self):
        """观察阶段循环场景内 PC 并返回观察结果 / Observe loops scene PCs and returns observations."""
        state = _overall_state(scene_id="tavern", plot_brief="酒馆异动", hints=["注意老板娘"])
        pc = SimpleNamespace(id="pc-1", scene_id="tavern")
        config = _char_repo_config([pc])
        observation = SceneObservation(pc_id="pc-1")
        with patch.object(
            character_service.observation_engine,
            "observe_scene",
            AsyncMock(return_value=observation),
        ) as mock_observe:
            result = await character_service.observe_scene(state, config)
        mock_observe.assert_awaited_once()
        assert result["scene_observations"] == [observation.model_dump()]

    @pytest.mark.asyncio
    async def test_decide_returns_empty_when_no_observations(self):
        """无观察结果时直接返回空动作 / Decide returns empty when no observations."""
        result = await character_service.decide(_overall_state())
        assert result == {"character_actions": []}

    @pytest.mark.asyncio
    async def test_decide_delegates_to_decision_engine(self):
        """决策阶段逐条观察结果调用 decision_engine / Decide delegates each observation to decision engine."""
        observations = [{"pc_id": "pc-1", "plot_brief": "战斗开始"}]
        action = {"pc_id": "pc-1", "type": "talk", "description": "先交涉"}
        with patch.object(
            character_service.decision_engine,
            "decide",
            AsyncMock(return_value=action),
        ) as mock_decide:
            result = await character_service.decide(
                _overall_state(
                    scene_observations=observations,
                    tick=3,
                    plot_brief="战斗开始",
                    scene_id="scene-1",
                )
            )
        mock_decide.assert_awaited_once_with(
            observation=observations[0],
            plot_brief="战斗开始",
            hints=[],
            scene_id="scene-1",
            tick=3,
            config=None,
        )
        assert result == {"character_actions": [action]}

    @pytest.mark.asyncio
    async def test_act_dispatches_talk_and_explore(self):
        """行动阶段逐条动作分发到 talk/exploration engine / Act dispatches each action to engines."""
        action = {"pc_id": "pc-1", "type": "talk"}
        state = _overall_state(
            tick=2,
            tick_message_id="msg-2",
            character_actions=[action],
        )
        with (
            patch.object(
                character_service.talk_engine,
                "process_talk_action",
                AsyncMock(),
            ) as mock_talk,
            patch.object(
                character_service.exploration_engine,
                "process_explore_action",
                AsyncMock(),
            ) as mock_explore,
        ):
            result = await character_service.act(state)
        mock_talk.assert_awaited_once_with(
            action=action,
            tick_message_id="msg-2",
            tick=2,
            config=None,
        )
        mock_explore.assert_awaited_once_with(
            action=action,
            tick_message_id="msg-2",
            tick=2,
            config=None,
        )
        assert result == {}


class TestSceneAndMessageService:
    """消息与场景服务测试 / Message and scene service tests."""

    @pytest.mark.asyncio
    async def test_create_tick_message_returns_message_id(self):
        """消息服务返回 tick_message_id / Message service returns tick_message_id."""
        with patch.object(
            message_service.message_engine,
            "create_tick_message",
            AsyncMock(return_value="tick-123"),
        ) as mock_create:
            result = await message_service.create_tick_message(_overall_state(tick=9))
        mock_create.assert_awaited_once()
        assert result == {"tick_message_id": "tick-123"}

    @pytest.mark.asyncio
    async def test_process_scene_calls_scene_engine_steps(self):
        """场景服务按顺序调用两个 scene engine / Scene service calls both scene steps."""
        state = _overall_state(
            tick=1, world_id="world-x", scene_id="scene-x", tick_message_id="msg-x"
        )
        with (
            patch.object(
                scene_service.scene_engine,
                "process_scene_setup",
                AsyncMock(),
            ) as mock_setup,
            patch.object(
                scene_service.scene_engine,
                "process_scene_objects",
                AsyncMock(),
            ) as mock_objects,
        ):
            result = await scene_service.process_scene(state)
        assert mock_setup.await_count == 1
        assert mock_objects.await_count == 1
        assert result == {}


class TestDMAndReflectionService:
    """DM 与反思服务测试 / DM and reflection service tests."""

    @pytest.mark.asyncio
    async def test_dm_create_maps_engine_response(self):
        """DM create 映射 engine 响应 / DM create maps engine response."""
        engine_result = SimpleNamespace(
            hints=["去酒馆"],
            plot_brief="今晚有冲突",
            scene_id="tavern",
            errors=[],
        )
        with patch.object(dm_service.dm_engine, "dm_create", AsyncMock(return_value=engine_result)):
            result = await dm_service.dm_create(_overall_state(tick=4, world_id="w-1"))
        assert result["hints"] == ["去酒馆"]
        assert result["plot_brief"] == "今晚有冲突"
        assert result["scene_id"] == "tavern"
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_dm_narrate_sets_needs_reflection_by_interval(self):
        """DM narrate 根据 interval 产生 needs_reflection / DM narrate sets reflection flag."""
        engine_result = SimpleNamespace(narrative_out="战斗爆发。", errors=[])
        config = {"configurable": {"reflection_interval": 5}}
        with patch.object(
            dm_service.dm_engine, "dm_narrate", AsyncMock(return_value=engine_result)
        ):
            result = await dm_service.dm_narrate(_overall_state(tick=10), config)
        assert result["narrative"] == "战斗爆发。"
        assert result["needs_reflection"] is True

    @pytest.mark.asyncio
    async def test_reflect_returns_empty_when_repos_missing(self):
        """缺少 repo 时反思服务安全降级 / Reflection falls back when repos are missing."""
        with patch("src.services.reflection_service.get_repo", side_effect=[None, None]):
            result = await reflection_service.reflect(
                {
                    "tick": 5,
                    "character_id": "pc-1",
                    "memories": [],
                    "tick_events": [],
                    "reflected_characters": [],
                    "summary_compressed": False,
                }
            )
        assert result == {"reflected_characters": []}
