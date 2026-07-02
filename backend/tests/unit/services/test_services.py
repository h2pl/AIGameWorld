"""Services 测试——对齐当前 graph/service/engine 结构。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.services import (
    character_service,
    dm_service,
    message_service,
    reflection_service,
    scene_service,
    summarizer_service,
)


def _overall_state(**overrides):
    """构造当前 OverallState 最小输入 / Build minimal OverallState input."""
    return {
        "tick": 0,
        "world_id": "world-1",
        "tick_message_id": "tick-msg-1",
        "scene_info": {},
        "hints": [],
        "plot_brief": "",
        "scene_id": "scene-1",
        "character_decisions": [],
        "narrative": "",
        "reflected_characters": [],
        "summary_compressed": False,
        "errors": [],
        "needs_reflection": False,
        **overrides,
    }


def _char_repo_config(pcs: list, object_ids: list[str] | None = None) -> dict:
    """构造带 char_repo/scene_repo 的 config / Build config with char/scene repo mocks."""
    object_ids = object_ids or []
    char_repo = AsyncMock()
    char_repo.load_pcs = AsyncMock(return_value=pcs)
    char_repo.load_actors = AsyncMock(return_value=[])
    scene_repo = AsyncMock()
    scene_repo.get_scene = AsyncMock(return_value=None)
    scene_repo.get_object_ids = AsyncMock(return_value=object_ids)
    scene_objects = {
        oid: SimpleNamespace(
            id=oid, name=oid, object_type=SimpleNamespace(value="prop"), interactable=True
        )
        for oid in object_ids
    }
    scene_repo.load_all = AsyncMock(return_value=scene_objects)
    return {"configurable": {"repos": {"char": char_repo, "scene": scene_repo}}}


class TestCharacterService:
    """角色服务测试 / Character service tests."""

    @pytest.mark.asyncio
    async def test_decide_returns_empty_when_no_pcs_in_scene(self):
        """没有 PC 时直接返回空 / Decide returns empty when there are no PCs in the scene."""
        result = await character_service.decide(_overall_state())
        assert result == {"character_decisions": []}

    @pytest.mark.asyncio
    async def test_decide_delegates_each_pc_to_decision_engine(self):
        """decide 逐个把场景内的 PC 交给 decision_engine / decide delegates each PC in the scene to decision_engine."""
        scene_info = {"pcs": [{"id": "pc-1"}], "scene_objects": [{"id": "obj-1"}]}
        decision = {"pc_id": "pc-1", "type": "talk", "description": "先交涉"}
        with patch.object(
            character_service.decision_engine,
            "decide",
            AsyncMock(return_value=decision),
        ) as mock_decide:
            result = await character_service.decide(
                _overall_state(
                    tick=3,
                    plot_brief="战斗开始",
                    scene_id="scene-1",
                    scene_info=scene_info,
                )
            )
        mock_decide.assert_awaited_once()
        assert mock_decide.call_args.kwargs["pc_id"] == "pc-1"
        assert mock_decide.call_args.kwargs["scene_info"] == scene_info
        assert mock_decide.call_args.kwargs["plot_brief"] == "战斗开始"
        assert mock_decide.call_args.kwargs["scene_id"] == "scene-1"
        assert mock_decide.call_args.kwargs["tick"] == 3
        assert result == {"character_decisions": [decision]}

    @pytest.mark.asyncio
    async def test_act_dispatches_talk_and_interact(self):
        """行动阶段逐条动作分发到 talk/interact/combat engine / Act dispatches each action to all engines."""
        decision = {"pc_id": "pc-1", "type": "talk"}
        state = _overall_state(
            tick=2,
            tick_message_id="msg-2",
            character_decisions=[decision],
        )
        with (
            patch.object(
                character_service.talk_engine,
                "process_talk_action",
                AsyncMock(return_value=None),
            ) as mock_talk,
            patch.object(
                character_service.interact_engine,
                "process_interact_action",
                AsyncMock(return_value=None),
            ) as mock_interact,
            patch.object(
                character_service.combat_engine,
                "process_combat_action",
                AsyncMock(return_value=None),
            ) as mock_combat,
        ):
            result = await character_service.act(state)
        mock_talk.assert_awaited_once_with(
            decision=decision,
            plot_brief="",
            hints=[],
            scene_id="scene-1",
            tick=2,
            config=None,
        )
        mock_interact.assert_awaited_once_with(
            decision=decision,
            config=None,
        )
        mock_combat.assert_awaited_once_with(
            decision=decision,
            config=None,
        )
        assert result == {"pending_events": []}


class TestSceneAndMessageService:
    """消息与场景服务测试 / Message and scene service tests."""

    @pytest.mark.asyncio
    async def test_create_tick_message_returns_message_id(self):
        """消息服务直接写 message_repo，返回 tick_message_id / Message service writes message_repo directly and returns tick_message_id."""
        message_repo = AsyncMock()
        config = {"configurable": {"repos": {"message": message_repo}}}
        result = await message_service.create_tick_message(_overall_state(tick=9), config)
        message_repo.insert.assert_awaited_once()
        assert result == {"tick_message_id": "tick_9"}

    @pytest.mark.asyncio
    async def test_create_tick_message_returns_empty_without_repo(self):
        """没有 message_repo 时降级为空 id / Falls back to an empty id when message_repo is missing."""
        result = await message_service.create_tick_message(_overall_state(tick=1))
        assert result == {"tick_message_id": ""}

    @pytest.mark.asyncio
    async def test_build_scene_info_returns_empty_without_repo(self):
        """没有 char_repo/scene_id 时返回空场景信息 / Returns empty scene info without char_repo/scene_id."""
        state = _overall_state(
            tick=1, world_id="world-x", scene_id="scene-x", tick_message_id="msg-x"
        )
        result = await scene_service.build_scene_info(state)
        assert result == {"scene_info": {}}

    @pytest.mark.asyncio
    async def test_build_scene_info_builds_scene_info(self):
        """场景服务构建当前场景的完整信息（不区分 PC）/ Scene service builds the current scene's full info (not per-PC)."""
        pc = SimpleNamespace(
            id="pc-1",
            scene_id="scene-1",
            name="Alex",
            role="fighter",
            race="human",
            status="active",
        )
        config = _char_repo_config([pc], object_ids=["obj-1"])
        state = _overall_state(tick=1, world_id="world-1", scene_id="scene-1")
        result = await scene_service.build_scene_info(state, config)
        info = result["scene_info"]
        assert [pc["id"] for pc in info["pcs"]] == ["pc-1"]
        assert [o["id"] for o in info["scene_objects"]] == ["obj-1"]


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


class TestSummarizerService:
    """摘要服务测试 / Summarizer service tests."""

    @pytest.mark.asyncio
    async def test_summarize_without_llm_not_compressed(self):
        """没有 LLM 时不压缩 / Without an LLM, not compressed."""
        result = await summarizer_service.summarize({"tick_events": [{"type": "e"}]})
        assert result["summary_compressed"] is False

    @pytest.mark.asyncio
    async def test_summarize_without_events_not_compressed(self):
        """没有事件时不压缩 / Without events, not compressed."""
        llm = AsyncMock()
        config = {"configurable": {"llm": llm}}
        result = await summarizer_service.summarize({"tick_events": []}, config)
        assert result["summary_compressed"] is False
        llm.call_structured.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarize_with_llm_compresses(self):
        """有 LLM + 事件时压缩成功 / With LLM + events, compression succeeds."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(return_value={"summary": "酒馆里发生了冲突。"})
        config = {"configurable": {"llm": llm}}
        result = await summarizer_service.summarize(
            {"tick_events": [{"type": "character_talk"}]}, config
        )
        assert result["summary_compressed"] is True
        assert result["summary_text"] == "酒馆里发生了冲突。"
