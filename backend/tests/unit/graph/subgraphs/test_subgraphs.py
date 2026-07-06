"""Graph Subgraphs 测试——对齐当前子图结构。"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.player_character import PlayerCharacter
from src.graph.subgraphs.pc_subgraph import pc_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph
from src.graph.subgraphs.scene_subgraph import scene_subgraph
from src.schemas.llm_output import (
    ActorGenerationSchema,
    GeneratedActorSchema,
    GeneratedSceneObjectSchema,
    SceneObjectGenerationSchema,
)


class TestCharacterSubgraph:
    """角色子图测试 / Character subgraph tests."""

    @pytest.mark.asyncio
    async def test_pc_subgraph_runs_decide_act_chain(self):
        """角色子图执行 decide → act 两阶段链路（场景信息已由 scene_service 提前构建好，不区分 PC）/ Subgraph runs decide → act (scene info precomputed by scene_service, not per-PC)."""
        scene = {"id": "tavern"}
        scene_objects = []
        pcs = {"pc-1": SimpleNamespace(id="pc-1", name="pc-1", role="", position_x=0, position_y=0)}
        state = {
            "tick": 1,
            "world_id": "world-1",
            "plot_brief": "酒馆起争执",
            "hints": [],
            "scene_id": "tavern",
            "pc_decisions": [],
            "scene": scene,
            "scene_objects": scene_objects,
            "pcs": pcs,
            "actors": {},
        }

        decision = [{"pc_id": "pc-1", "type": "talk", "description": "先问话"}]
        with (
            patch(
                "src.services.pc_service.decision_engine.decide",
                AsyncMock(return_value=decision),
            ),
            patch(
                "src.services.pc_service.talk_engine.process_talk_action",
                AsyncMock(),
            ),
            patch(
                "src.services.pc_service.interact_engine.process_interact_action",
                AsyncMock(),
            ),
            patch(
                "src.services.pc_service.combat_engine.process_combat_action",
                AsyncMock(),
            ),
        ):
            result = await pc_subgraph.ainvoke(state)
        assert result["scene"] == scene
        assert result["pc_decisions"] == decision


class TestReflectionSubgraph:
    """反思子图测试 / Reflection subgraph tests."""

    @pytest.mark.asyncio
    async def test_reflection_subgraph_runs_single_node(self):
        """反思子图执行单节点反思 / Reflection subgraph runs single reflection node."""
        state = {
            "tick": 5,
            "pc_id": "pc-1",
            "memories": [],
            "tick_events": [],
            "reflected_pcs": [],
            "summary_compressed": False,
        }
        with patch("src.services.reflection_service.get_repo", side_effect=[None, None]):
            result = await reflection_subgraph.ainvoke(state)
        # ainvoke 返回合并后的完整状态，而不仅是节点的返回值 / ainvoke returns the merged full state
        assert result["reflected_pcs"] == []


class TestSceneSubgraph:
    """场景子图测试 / Scene subgraph tests."""

    @pytest.mark.asyncio
    async def test_scene_subgraph_builds_scene_state(self):
        """场景子图依次执行 6 个节点并产出 scene/scene_objects/pcs/actors / Subgraph runs 6 nodes and produces scene state."""
        pc = SimpleNamespace(
            id="pc-1",
            scene_id="scene-1",
            name="Alex",
            role="fighter",
            race="human",
            status="active",
            position_x=0,
            position_y=0,
        )
        pc_repo = AsyncMock()
        pc_repo.load_all = AsyncMock(return_value=[pc])
        pc_repo.load_one = AsyncMock(return_value=None)

        scene = {
            "id": "scene-1",
            "name": "Tavern",
            "type": "indoor",
            "description": "一个热闹的酒馆。",
            "map_key": "tavern",
            "spawn_x": 10,
            "spawn_y": 10,
            "map_width": 40,
            "map_height": 40,
            "landmarks": [],
            "exits": [],
            "ext_json": "{}",
        }
        obj = SimpleNamespace(
            id="obj-1",
            name="Chest",
            object_type=SimpleNamespace(value="container"),
            interactable=True,
            position_x=1,
            position_y=1,
            interact_data={},
        )
        scene_repo = AsyncMock()
        scene_repo.get_scene = AsyncMock(return_value=scene)
        scene_repo.get_object_ids = AsyncMock(return_value=["obj-1"])
        scene_repo.load_all = AsyncMock(return_value={"obj-1": obj})

        actor_repo = AsyncMock()
        actor_repo.load_all = AsyncMock(return_value=[])

        config = {
            "configurable": {
                "repos": {
                    "char": pc_repo,
                    "scene": scene_repo,
                    "actor": actor_repo,
                }
            }
        }
        state = {
            "tick": 1,
            "world_id": "world-1",
            "scene_id": "scene-1",
            "pc_decisions": [],
            "pending_actions": [],
        }
        result = await scene_subgraph.ainvoke(state, config)
        assert result["scene"]["id"] == "scene-1"
        assert [o["id"] for o in result["scene_objects"]] == ["obj-1"]
        assert "pc-1" in result["pcs"]
        assert result["actors"] == {}

    @pytest.mark.asyncio
    async def test_scene_subgraph_generates_actors_and_objects_when_empty(self):
        """场景为空时 LLM 动态生成 Actor 和 SceneObject / Subgraph spawns actors and objects via LLM when empty."""
        pc = PlayerCharacter(
            id="pc-1",
            scene_id="scene-1",
            name="Alex",
            role="fighter",
            position_x=0,
            position_y=0,
        )
        pc_repo = AsyncMock()
        pc_repo.load_all = AsyncMock(return_value=[pc])
        pc_repo.load_one = AsyncMock(return_value=None)

        scene = {
            "id": "scene-1",
            "name": "Tavern",
            "type": "indoor",
            "description": "一个热闹的酒馆。",
            "spawn_x": 10,
            "spawn_y": 10,
            "map_width": 40,
            "map_height": 40,
        }
        saved_objects: dict[str, Any] = {}

        def _store_object(o):
            """把生成的 object 存入 saved_objects / Store generated object."""
            saved_objects[o.id] = o

        scene_repo = AsyncMock()
        scene_repo.get_scene = AsyncMock(return_value=scene)
        scene_repo.get_object_ids = AsyncMock(side_effect=lambda sid: list(saved_objects.keys()))
        scene_repo.save_object = AsyncMock(side_effect=_store_object)
        scene_repo.load_all = AsyncMock(return_value=saved_objects)

        saved_actors: list = []
        actor_repo = AsyncMock()
        actor_repo.load_all = AsyncMock(return_value=saved_actors)
        actor_repo.save = AsyncMock(side_effect=saved_actors.append)

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            side_effect=lambda purpose, schema, messages: (
                ActorGenerationSchema(
                    actors=[
                        GeneratedActorSchema(
                            id="actor_bartender",
                            name="酒保",
                            role="bartender",
                            position_x=12,
                            position_y=10,
                        )
                    ]
                )
                if purpose == "spawn_actors"
                else SceneObjectGenerationSchema(
                    objects=[
                        GeneratedSceneObjectSchema(
                            id="obj_barrel",
                            name="酒桶",
                            object_type="container",
                            position_x=11,
                            position_y=10,
                        )
                    ]
                )
            )
        )

        config = {
            "configurable": {
                "repos": {
                    "char": pc_repo,
                    "scene": scene_repo,
                    "actor": actor_repo,
                },
                "llm": llm,
            }
        }
        state = {
            "tick": 1,
            "world_id": "world-1",
            "scene_id": "scene-1",
            "pc_decisions": [],
            "pending_actions": [],
        }
        result = await scene_subgraph.ainvoke(state, config)
        assert result["scene"]["id"] == "scene-1"
        assert "actor_bartender" in result["actors"]
        assert any(o["id"] == "obj_barrel" for o in result["scene_objects"])
        assert "pc-1" in result["pcs"]
        actor_repo.save.assert_awaited_once()
        scene_repo.save_object.assert_awaited_once()
