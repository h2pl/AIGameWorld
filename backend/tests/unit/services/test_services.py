"""Services 测试——对齐当前 graph/service/engine 结构。"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.player_character import PlayerCharacter
from src.schemas.llm_output import (
    ActorGenerationSchema,
    GeneratedActorSchema,
    GeneratedSceneObjectSchema,
    SceneObjectGenerationSchema,
    TilemapInterpretationSchema,
)
from src.services import (
    dm_service,
    event_service,
    pc_service,
    reflection_service,
    scene_service,
    summarizer_service,
)


def _overall_state(**overrides):
    """构造当前 OverallState 最小输入 / Build minimal OverallState input."""
    return {
        "tick": 0,
        "world_id": "world-1",
        "scene": {},
        "scene_objects": [],
        "pending_actions": [],
        "hints": [],
        "plot_brief": "",
        "scene_id": "scene-1",
        "pc_decisions": [],
        "narrative": "",
        "pcs": {},
        "actors": {},
        **overrides,
    }


def _pc_repo_config(pcs: list, object_ids: list[str] | None = None) -> dict:
    """构造带 pc_repo/scene_repo 的 config / Build config with char/scene repo mocks."""
    object_ids = object_ids or []
    pc_repo = AsyncMock()
    pc_repo.load_all = AsyncMock(return_value=pcs)
    pc_repo.load_one = AsyncMock(return_value=None)
    scene_repo = AsyncMock()
    scene_repo.get_scene = AsyncMock(return_value=None)
    scene_repo.get_object_ids = AsyncMock(return_value=object_ids)
    scene_objects = {
        oid: SimpleNamespace(
            id=oid,
            name=oid,
            object_type=SimpleNamespace(value="prop"),
            interactable=True,
            position_x=1,
            position_y=1,
            interact_data={},
        )
        for oid in object_ids
    }
    scene_repo.load_all = AsyncMock(return_value=scene_objects)
    return {"configurable": {"repos": {"char": pc_repo, "scene": scene_repo}}}


class TestCharacterService:
    """角色服务测试 / Character service tests."""

    @pytest.mark.asyncio
    async def test_decide_returns_empty_when_no_pcs_in_scene(self):
        """没有 PC 时直接返回空 / Decide returns empty when there are no PCs in the scene."""
        result = await pc_service.decide(_overall_state())
        assert result == {"pc_decisions": []}

    @pytest.mark.asyncio
    async def test_decide_delegates_each_pc_to_decision_engine(self):
        """decide 逐个把场景内的 PC 交给 decision_engine / decide delegates each PC in the scene to decision_engine."""
        scene = {"id": "scene-1"}
        scene_objects = [{"id": "obj-1"}]
        pcs = {"pc-1": PlayerCharacter(id="pc-1", name="Alex", role="fighter")}
        decision = [{"pc_id": "pc-1", "type": "talk", "description": "先交涉"}]
        with patch.object(
            pc_service.decision_engine,
            "decide",
            AsyncMock(return_value=decision),
        ) as mock_decide:
            result = await pc_service.decide(
                _overall_state(
                    tick=3,
                    plot_brief="战斗开始",
                    scene_id="scene-1",
                    scene=scene,
                    scene_objects=scene_objects,
                    pcs=pcs,
                )
            )
        mock_decide.assert_awaited_once()
        assert mock_decide.call_args.kwargs["pc_id"] == "pc-1"
        assert mock_decide.call_args.kwargs["scene"] == scene
        assert mock_decide.call_args.kwargs["plot_brief"] == "战斗开始"
        assert mock_decide.call_args.kwargs["scene_id"] == "scene-1"
        assert mock_decide.call_args.kwargs["tick"] == 3
        assert mock_decide.call_args.kwargs["pcs"] == pcs
        assert mock_decide.call_args.kwargs["scene_objects"] == scene_objects
        assert result == {"pc_decisions": decision}

    @pytest.mark.asyncio
    async def test_act_dispatches_talk_and_interact(self):
        """行动阶段逐条动作分发到 talk/interact/combat engine / Act dispatches each action to all engines."""
        decision = {"pc_id": "pc-1", "type": "talk"}
        state = _overall_state(
            tick=2,
            pc_decisions=[decision],
        )
        with (
            patch.object(
                pc_service.talk_engine,
                "process_talk_action",
                AsyncMock(return_value=None),
            ) as mock_talk,
            patch.object(
                pc_service.interact_engine,
                "process_interact_action",
                AsyncMock(return_value=None),
            ) as mock_interact,
            patch.object(
                pc_service.combat_engine,
                "process_combat_action",
                AsyncMock(return_value=None),
            ) as mock_combat,
        ):
            result = await pc_service.act(state)
        mock_talk.assert_awaited_once_with(
            decision=decision,
            plot_brief="",
            hints=[],
            scene_id="scene-1",
            tick=2,
            pcs={},
            actors={},
            pc_memory_map={},
            config=None,
        )
        mock_interact.assert_awaited_once_with(
            decision=decision,
            scene={},
            scene_objects=[],
            pcs={},
            actors={},
            tick=2,
            plot_brief="",
            hints=[],
            pc_memory_map={},
            config=None,
        )
        mock_combat.assert_awaited_once_with(
            decision=decision,
            scene={},
            pcs={},
            actors={},
            plot_brief="",
            hints=[],
            tick=2,
            pc_memory_map={},
            config=None,
        )
        assert result == {"pending_actions": []}

    @pytest.mark.asyncio
    async def test_act_formats_action_result_uniformly(self):
        """把命中的 engine 结果格式化成 {order, action_type, target_id, target_type, result} /
        Format the matching engine's result into {order, action_type, target_id, target_type, result}."""
        decision = {"pc_id": "pc-1", "type": "talk", "target_id": "pc-2", "target_type": "pc"}
        talk_result = {"kind": "pc_talk", "participants": ["pc-1", "pc-2"], "turns": []}
        state = _overall_state(pc_decisions=[decision])
        with (
            patch.object(
                pc_service.talk_engine,
                "process_talk_action",
                AsyncMock(return_value=talk_result),
            ),
            patch.object(
                pc_service.interact_engine,
                "process_interact_action",
                AsyncMock(return_value=None),
            ),
            patch.object(
                pc_service.combat_engine,
                "process_combat_action",
                AsyncMock(return_value=None),
            ),
        ):
            result = await pc_service.act(state)
        assert result == {
            "pending_actions": [
                {
                    "order": 0,
                    "pc_id": "pc-1",
                    "action_type": "talk",
                    "target_id": "pc-2",
                    "target_type": "pc",
                    "result": talk_result,
                }
            ]
        }


class TestSceneAndMessageService:
    """场景服务测试 / Scene service tests."""

    @pytest.mark.asyncio
    async def test_build_scene_state_returns_empty_without_repo(self):
        """没有 repo 时仍返回场景上下文，PC/Actor map 为空 / Returns scene context with empty state maps when repos are missing."""
        state = _overall_state(tick=1, world_id="world-x", scene_id="scene-x")
        result = await scene_service.build_scene_state(state)
        assert result["pcs"] == {}
        assert result["actors"] == {}
        assert result["scene"]["id"] == "scene-x"

    @pytest.mark.asyncio
    async def test_build_scene_state_builds_scene_state(self):
        """场景服务构建当前场景的完整信息 / Scene service builds the current scene's full info."""
        pc = PlayerCharacter(
            id="pc-1",
            scene_id="scene-1",
            name="Alex",
            role="fighter",
            race="human",
            status="active",
            position_x=0,
            position_y=0,
        )
        config = _pc_repo_config([pc], object_ids=["obj-1"])
        state = _overall_state(tick=1, world_id="world-1", scene_id="scene-1")
        result = await scene_service.build_scene_state(state, config)
        assert "pc-1" in result["pcs"]
        assert [o["id"] for o in result["scene_objects"]] == ["obj-1"]


class TestDMAndReflectionService:
    """DM 与反思服务测试 / DM and reflection service tests."""

    @pytest.mark.asyncio
    async def test_dm_create_maps_engine_response(self):
        """DM create 映射 engine 响应 / DM create maps engine response."""
        engine_result = SimpleNamespace(
            hints=["去酒馆"],
            plot_brief="今晚有冲突",
            scene_id="tavern",
            ext=None,
        )
        with patch.object(dm_service.dm_engine, "dm_create", AsyncMock(return_value=engine_result)):
            result = await dm_service.dm_create(_overall_state(tick=4, world_id="w-1"))
        assert result["hints"] == ["去酒馆"]
        assert result["plot_brief"] == "今晚有冲突"
        assert result["scene_id"] == "tavern"
        assert result["_dm_ext"] is None

    @pytest.mark.asyncio
    async def test_dm_narrate_returns_narrative(self):
        """DM narrate 返回叙事文本 / DM narrate returns narrative text."""
        engine_result = SimpleNamespace(narrative_out="战斗爆发。")
        with patch.object(
            dm_service.dm_engine, "dm_narrate", AsyncMock(return_value=engine_result)
        ):
            result = await dm_service.dm_narrate(_overall_state(tick=10))
        assert result["narrative"] == "战斗爆发。"

    @pytest.mark.asyncio
    async def test_reflect_returns_empty_when_repos_missing(self):
        """缺少 repo 时反思服务安全降级 / Reflection falls back when repos are missing."""
        with patch("src.services.reflection_service.get_repo", side_effect=[None, None]):
            result = await reflection_service.reflect(
                {
                    "tick": 5,
                    "pc_id": "pc-1",
                    "memories": [],
                    "tick_events": [],
                    "reflected_pcs": [],
                    "summary_compressed": False,
                }
            )
        assert result == {"reflected_pcs": []}


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
        from src.schemas.llm_output import SummaryOutputSchema

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=SummaryOutputSchema(summary="酒馆里发生了冲突。")
        )
        config = {"configurable": {"llm": llm}}
        result = await summarizer_service.summarize({"tick_events": [{"type": "pc_talk"}]}, config)
        assert result["summary_compressed"] is True
        assert result["summary_text"] == "酒馆里发生了冲突。"


class TestEventService:
    """事件服务测试 / Event service tests."""

    @pytest.mark.asyncio
    async def test_flush_events_persists_events_then_marks_ready(self):
        """先落盘事件，再把消息标记为可消费 / Persist events first, then mark the message ready."""
        event_repo = AsyncMock()
        config = {"configurable": {"repos": {"event": event_repo}}}
        state = _overall_state(
            tick=3,
            scene_id="",
            pending_actions=[
                {
                    "order": 0,
                    "action_type": "talk",
                    "target_id": "pc-2",
                    "target_type": "pc",
                    "result": {"kind": "pc_talk", "pc_id": "pc-1"},
                }
            ],
        )
        result = event_service.flush_events(state, config)
        events = result.get("_pending_events", [])
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_flush_events_marks_ready_even_without_pending_events(self):
        """没有待落盘事件也要标记消息可消费（如纯叙事 tick）/
        Mark the message ready even with no pending events (e.g. narrative-only ticks)."""
        event_repo = AsyncMock()
        config = {"configurable": {"repos": {"event": event_repo}}}
        state = _overall_state(tick=4, scene_id="", pending_actions=[])
        result = event_service.flush_events(state, config)
        events = result.get("_pending_events", [])
        assert events == []

    @pytest.mark.asyncio
    async def test_flush_events_builds_scene_setup_from_scene(self):
        """从 scene_service 写入的 scene 构造 scene_setup 事件 /
        Build a scene_setup event from the scene state scene_service wrote."""
        event_repo = AsyncMock()
        config = {"configurable": {"repos": {"event": event_repo}}}
        state = _overall_state(
            tick=1,
            scene_id="",
            scene={"id": "scene-1", "name": "Tavern"},
            scene_objects=[{"id": "obj-1", "name": "Chest", "object_type": "container"}],
            pcs={"pc-1": PlayerCharacter(id="pc-1", name="Alex")},
            actors={},
            pending_actions=[],
        )
        result = event_service.flush_events(state, config)
        events = result.get("_pending_events", [])
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_flush_events_builds_dm_create_from_state(self):
        """从 dm_service.dm_create 写入的 plot_brief/hints/scene_id 构造 dm_create 事件 /
        Build a dm_create event from the plot_brief/hints/scene_id dm_service.dm_create wrote."""
        event_repo = AsyncMock()
        config = {"configurable": {"repos": {"event": event_repo}}}
        state = _overall_state(
            tick=0,
            scene_id="scene-1",
            plot_brief="酒馆冲突一触即发。",
            hints=["注意角落里的陌生人"],
            pending_actions=[],
        )
        result = event_service.flush_events(state, config)
        events = result.get("_pending_events", [])
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_flush_events_builds_pc_decision_events(self):
        """从 pc_decisions 构造 pc_decision 事件 / Build pc_decision events from pc_decisions."""
        event_repo = AsyncMock()
        config = {"configurable": {"repos": {"event": event_repo}}}
        state = _overall_state(
            tick=2,
            scene_id="",
            pcs={"pc-1": PlayerCharacter(id="pc-1", name="Alex")},
            pc_decisions=[
                {
                    "pc_id": "pc-1",
                    "type": "talk",
                    "target_id": "npc-1",
                    "target_type": "actor",
                    "thought": "我想找 NPC 打听消息。",
                    "description": "先交谈收集情报。",
                }
            ],
            pending_actions=[],
        )
        result = event_service.flush_events(state, config)
        events = result.get("_pending_events", [])
        decision_events = [e for e in events if e.type.value == "pc_decision"]
        assert len(decision_events) == 1
        assert decision_events[0].payload["pc_id"] == "pc-1"
        assert decision_events[0].payload["thought"] == "我想找 NPC 打听消息。"
        assert decision_events[0].payload["reasoning"] == "先交谈收集情报。"

    @pytest.mark.asyncio
    async def test_flush_events_drops_unknown_kinds(self):
        """未在已知 action 类型内的原始结果（如未结算的 character_combat）不落盘 /
        Raw results outside known action types (e.g. unresolved character_combat) are dropped."""
        event_repo = AsyncMock()
        config = {"configurable": {"repos": {"event": event_repo}}}
        state = _overall_state(
            tick=1,
            scene_id="",
            pending_actions=[
                {
                    "order": 0,
                    "action_type": "character_combat",
                    "target_id": "npc-1",
                    "target_type": "actor",
                    "result": {"kind": "character_combat", "pc_id": "pc-1"},
                }
            ],
        )
        result = event_service.flush_events(state, config)
        events = result.get("_pending_events", [])
        assert events == []

    @pytest.mark.asyncio
    async def test_flush_events_does_not_include_narrative(self):
        """flush_events 不处理 narrative，narrative 由 emit_narrative_event 追加 /
        flush_events ignores narrative; emit_narrative_event appends it."""
        event_repo = AsyncMock()
        config = {"configurable": {"repos": {"event": event_repo}}}
        state = _overall_state(
            tick=2,
            scene_id="",
            pending_actions=[],
            narrative="夜幕降临，酒馆里灯火通明。",
        )
        result = event_service.flush_events(state, config)
        events = result.get("_pending_events", [])
        assert events == []

    @pytest.mark.asyncio
    async def test_emit_narrative_event_appends_dm_narrative(self):
        """emit_narrative_event 把 state.narrative 追加为 dm_narrative 事件 /
        emit_narrative_event converts state.narrative into a dm_narrative event."""
        state = _overall_state(
            tick=2,
            scene_id="",
            pending_actions=[],
            narrative="夜幕降临，酒馆里灯火通明。",
        )
        result = event_service.emit_narrative_event(state)
        events = result.get("_pending_events", [])
        assert len(events) == 1
        assert events[0].type.value == "dm_narrative"
        assert events[0].payload["text"] == "夜幕降临，酒馆里灯火通明。"

    @pytest.mark.asyncio
    async def test_emit_narrative_event_skips_empty_narrative(self):
        """narrative 为空时不追加 dm_narrative 事件 /
        Empty narrative does not create a dm_narrative event."""
        state = _overall_state(
            tick=2,
            scene_id="",
            pending_actions=[],
            narrative="",
        )
        result = event_service.emit_narrative_event(state)
        events = result.get("_pending_events", [])
        assert events == []


class TestSpawnService:
    """动态生成 Actor / SceneObject 测试 / Dynamic spawn service tests."""

    @pytest.mark.asyncio
    async def test_generate_actors_skips_when_scene_has_actors(self):
        """当前场景已有 Actor 时跳过生成 / Skip actor generation when scene already has actors."""
        actor_repo = AsyncMock()
        actor_repo.load_all = AsyncMock(return_value=[SimpleNamespace(id="a1", scene_id="scene-1")])
        actor_repo.save = AsyncMock()
        config = {"configurable": {"repos": {"actor": actor_repo}}}
        state = _overall_state(world_id="w-1", scene_id="scene-1", scene={"id": "scene-1"})
        result = await scene_service.generate_actors(state, config)
        assert result["_generated_actors"] == []
        actor_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_actors_saves_llm_generated_actors(self):
        """场景无 Actor 时 LLM 生成并保存 / LLM generates and saves actors when scene is empty."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=ActorGenerationSchema(
                actors=[
                    GeneratedActorSchema(
                        id="actor_bartender",
                        name="酒保",
                        role="bartender",
                        race="human",
                        disposition="neutral",
                        position_x=10,
                        position_y=10,
                    )
                ]
            )
        )
        saved = []
        actor_repo = AsyncMock()
        actor_repo.load_all = AsyncMock(return_value=[])
        actor_repo.save = AsyncMock(side_effect=saved.append)
        config = {
            "configurable": {
                "repos": {"actor": actor_repo},
                "llm": llm,
            }
        }
        state = _overall_state(
            world_id="w-1",
            scene_id="scene-1",
            scene={"id": "scene-1", "name": "Tavern", "map_width": 40, "map_height": 40},
            plot_brief="酒馆里暗流涌动。",
        )
        result = await scene_service.generate_actors(state, config)
        assert result["_generated_actors"] == ["actor_bartender"]
        assert len(saved) == 1
        assert saved[0].id == "actor_bartender"
        assert saved[0].scene_id == "scene-1"
        assert saved[0].world_id == "w-1"

    @pytest.mark.asyncio
    async def test_generate_scene_objects_skips_when_scene_has_objects(self):
        """当前场景已有物体时跳过生成 / Skip object generation when scene already has objects."""
        scene_repo = AsyncMock()
        scene_repo.get_object_ids = AsyncMock(return_value=["obj-1"])
        scene_repo.save_object = AsyncMock()
        config = {"configurable": {"repos": {"scene": scene_repo}}}
        state = _overall_state(world_id="w-1", scene_id="scene-1", scene={"id": "scene-1"})
        result = await scene_service.generate_scene_objects(state, config)
        assert result["_generated_scene_objects"] == []
        scene_repo.save_object.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_scene_objects_saves_llm_generated_objects(self):
        """场景无物体时 LLM 生成并保存 / LLM generates and saves objects when scene is empty."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=SceneObjectGenerationSchema(
                objects=[
                    GeneratedSceneObjectSchema(
                        id="obj_chest",
                        name="宝箱",
                        object_type="container",
                        position_x=5,
                        position_y=5,
                        interact_data={"locked": False},
                    )
                ]
            )
        )
        saved = []
        scene_repo = AsyncMock()
        scene_repo.get_object_ids = AsyncMock(return_value=[])
        scene_repo.save_object = AsyncMock(side_effect=saved.append)
        scene_repo.load_all = AsyncMock(return_value={})
        config = {
            "configurable": {
                "repos": {"scene": scene_repo},
                "llm": llm,
            }
        }
        state = _overall_state(
            world_id="w-1",
            scene_id="scene-1",
            scene={"id": "scene-1", "name": "Tavern", "map_width": 40, "map_height": 40},
            plot_brief="酒馆里暗流涌动。",
            actors={},
        )
        result = await scene_service.generate_scene_objects(state, config)
        assert result["_generated_scene_objects"] == ["obj_chest"]
        assert len(saved) == 1
        assert saved[0].id == "obj_chest"
        assert saved[0].scene_id == "scene-1"
        assert saved[0].world_id == "w-1"


class TestTilemapService:
    """Tilemap 语义解读测试 / Tilemap interpretation service tests."""

    @pytest.mark.asyncio
    async def test_interpret_tilemap_skips_when_summary_exists(self):
        """已有 tilemap_summary 时跳过 LLM / Skip interpretation when summary already exists."""
        scene_repo = AsyncMock()
        scene_repo.save_tilemap_summary = AsyncMock()
        config = {"configurable": {"repos": {"scene": scene_repo}}}
        state = _overall_state(
            scene_id="scene-1",
            scene={"id": "scene-1", "tilemap_summary": "已有摘要"},
        )
        result = await scene_service.interpret_tilemap(state, config)
        assert result["scene"]["tilemap_summary"] == "已有摘要"
        scene_repo.save_tilemap_summary.assert_not_called()

    @pytest.mark.asyncio
    async def test_interpret_tilemap_skips_when_no_tilemap_file(self):
        """找不到 tilemap 文件时跳过 / Skip when tilemap file is missing."""
        scene_repo = AsyncMock()
        scene_repo.save_tilemap_summary = AsyncMock()
        config = {"configurable": {"repos": {"scene": scene_repo}}}
        state = _overall_state(
            scene_id="scene-1",
            scene={"id": "scene-1", "map_key": "not-exist"},
        )
        result = await scene_service.interpret_tilemap(state, config)
        assert result["scene"].get("tilemap_summary", "") == ""
        scene_repo.save_tilemap_summary.assert_not_called()

    @pytest.mark.asyncio
    async def test_interpret_tilemap_generates_and_saves_summary(self):
        """读取 tilemap 文件，LLM 生成摘要并保存 / Generate and save tilemap summary via LLM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assets_dir = Path(tmpdir)
            tilemap = {
                "width": 10,
                "height": 10,
                "tilewidth": 32,
                "tileheight": 32,
                "orientation": "orthogonal",
                "layers": [
                    {"name": "Ground", "type": "tilelayer", "visible": True, "data": [1] * 100}
                ],
                "tilesets": [
                    {"name": "TestSet", "image": "test.png", "tilewidth": 32, "tileheight": 32}
                ],
                "properties": {},
            }
            (assets_dir / "scene-1.json").write_text(json.dumps(tilemap), encoding="utf-8")

            llm = AsyncMock()
            llm.call_structured = AsyncMock(
                return_value=TilemapInterpretationSchema(summary="一片荒凉的沙漠，中央有口水井。")
            )
            scene_repo = AsyncMock()
            scene_repo.save_tilemap_summary = AsyncMock()
            config = {
                "configurable": {
                    "repos": {"scene": scene_repo},
                    "llm": llm,
                }
            }
            state = _overall_state(
                scene_id="scene-1",
                scene={"id": "scene-1", "map_key": "scene-1"},
            )
            result = await scene_service.interpret_tilemap(state, config, assets_dir=assets_dir)
            assert result["scene"]["tilemap_summary"] == "一片荒凉的沙漠，中央有口水井。"
            scene_repo.save_tilemap_summary.assert_awaited_once_with(
                "scene-1", "一片荒凉的沙漠，中央有口水井。"
            )

    def test_summarize_tilemap_compacts_layer_data(self):
        """_summarize_tilemap 不发送完整 data 数组 / Summarizer excludes full data arrays."""
        tilemap = {
            "width": 2,
            "height": 2,
            "tilewidth": 32,
            "tileheight": 32,
            "orientation": "orthogonal",
            "layers": [
                {"name": "Ground", "type": "tilelayer", "visible": True, "data": [1, 2, 3, 4]}
            ],
            "tilesets": [{"name": "Set", "image": "set.png", "tilewidth": 32, "tileheight": 32}],
            "properties": {"foo": "bar"},
        }
        text = scene_service._summarize_tilemap(tilemap)
        assert "地图尺寸: 2x2" in text
        assert "Ground" in text
        assert "non_empty_tiles=4" in text
        assert "[1, 2, 3, 4]" not in text
