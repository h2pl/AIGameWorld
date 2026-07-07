"""Graph Subgraphs 测试——对齐当前子图结构。"""

from unittest.mock import AsyncMock, patch

import pytest

from src.domain import Decision, Scene, SceneObject, SceneObjectType
from src.domain.player_character import PlayerCharacter
from src.graph.subgraphs.load_data_subgraph import load_data_subgraph
from src.graph.subgraphs.pc_subgraph import pc_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph
from src.graph.subgraphs.tick_init_subgraph import tick_init_subgraph


class TestCharacterSubgraph:
    """角色子图测试 / Character subgraph tests."""

    @pytest.mark.asyncio
    async def test_pc_subgraph_runs_decide_act_chain(self):
        """角色子图执行 decide → act 两阶段链路（场景信息已由 tick_init_service 提前构建好，不区分 PC）/ Subgraph runs decide → act (scene info precomputed by tick_init_service, not per-PC)."""
        scene = Scene(id="tavern")
        scene_objects: list[SceneObject] = []
        pcs = {"pc-1": PlayerCharacter(id="pc-1", name="pc-1", role="", position_x=0, position_y=0)}
        state = {
            "tick": 1,
            "world_id": "world-1",
            
            "dm_record": None,
            "scene_id": "tavern",
            "pc_decisions": [],
            "scene": scene,
            "scene_objects": scene_objects,
            "pcs": pcs,
            "actors": {},
        }

        decision = Decision(pc_id="pc-1", type="talk", description="先问话")
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
        assert result["pc_decisions"] == [decision]


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


class TestLoadDataSubgraph:
    """数据加载子图测试 / Load data subgraph tests."""

    @pytest.mark.asyncio
    async def test_load_data_subgraph_loads_state(self):
        """数据加载子图依次执行 4 个节点并产出 scene/scene_objects/pcs/actors / Load data subgraph produces full state."""
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
        pc_repo = AsyncMock()
        pc_repo.load_all = AsyncMock(return_value=[pc])

        scene = Scene(
            id="scene-1",
            name="Tavern",
            type="indoor",
            description="一个热闹的酒馆。",
            spawn_x=10,
            spawn_y=10,
            map_width=40,
            map_height=40,
        )
        obj = SceneObject(
            id="obj-1",
            name="Chest",
            object_type=SceneObjectType.CONTAINER,
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
            "actions": [],
        }
        result = await load_data_subgraph.ainvoke(state, config)
        assert result["scene"].id == "scene-1"
        assert [o.id for o in result["scene_objects"]] == ["obj-1"]
        assert "pc-1" in result["pcs"]
        assert result["actors"] == {}


class TestTickInitSubgraph:
    """tick 初始化子图测试 / Tick init subgraph tests."""

    @pytest.mark.asyncio
    async def test_tick_init_subgraph_assigns_positions(self):
        """tick 初始化子图为未设坐标的 PC 分配出生点 / Assigns spawn positions to unset PCs."""
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
        scene = Scene(
            id="scene-1",
            name="Tavern",
            type="indoor",
            description="一个热闹的酒馆。",
            spawn_x=10,
            spawn_y=10,
            map_width=40,
            map_height=40,
        )
        state = {
            "tick": 1,
            "world_id": "world-1",
            "scene_id": "scene-1",
            "scene": scene,
            "actors": {},
            "pcs": {"pc-1": pc},
            "pc_decisions": [],
            "actions": [],
        }
        result = await tick_init_subgraph.ainvoke(state)
        assigned = result["pcs"]["pc-1"]
        assert (assigned.position_x, assigned.position_y) != (0, 0)
        assert assigned.scene_id == "scene-1"
