"""Graph Subgraphs 测试——对齐当前子图结构。"""

from unittest.mock import AsyncMock, patch

import pytest

from src.domain import Decision, DMRecord, Scene, SceneObject
from src.domain.player_character import PlayerCharacter
from src.graph.graph import build_tick_graph
from src.graph.subgraphs.pc_subgraph import pc_subgraph
from src.services import data_service


class TestPcSubgraph:
    """角色子图测试 / PC subgraph tests."""

    @pytest.mark.asyncio
    async def test_pc_subgraph_runs_decide_act_chain(self):
        """角色子图执行 decide → act 两阶段链路（场景信息已由 world_init/party/tick_init 提前构建好，不区分 PC）/ Subgraph runs decide → act (scene info precomputed by world_init/party/tick_init, not per-PC)."""
        scene = Scene(id="tavern")
        scene_objects: list[SceneObject] = []
        pcs = {"pc-1": PlayerCharacter(id="pc-1", name="pc-1", role="", position_x=0, position_y=0)}
        state = {
            "tick": 1,
            "world_id": "world-1",
            "dm_record": None,
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


class TestLoadDataSubgraph:
    """数据加载子图测试 / Load data subgraph tests."""

    @pytest.mark.asyncio
    async def test_load_scene_from_current_scene_id(self):
        """load_scene 从 current_scene_id 读取场景（确定性路径，不依赖 dm_record）/
        load_scene reads scene via current_scene_id, not dm_record."""
        scene = Scene(
            id="scene-1",
            name="Tavern",
            type="indoor",
            description="test",
            spawn_x=10,
            spawn_y=10,
            map_width=40,
            map_height=40,
        )
        scene_repo = AsyncMock()
        scene_repo.get_scene = AsyncMock(return_value=scene)
        config = {"configurable": {"repos": {"scene": scene_repo}}}
        # current_scene_id 由 world_init / party.decide_scene 持久化，dm_record 不再携带场景
        state = {
            "tick": 1,
            "current_scene_id": "scene-1",
            "dm_record": DMRecord(tick=1, world_id="w-1"),
        }
        result = await data_service.load_scene(state, config)
        assert result["scene"].id == "scene-1"


class TestTickInitConditionalEdges:
    """主图统一流程测试 / Main-graph uniform per-tick flow tests."""

    def test_main_graph_compiles(self):
        """主图可正常编译，所有 tick 走统一流程（world 初始化已在图外守卫）/ Main graph compiles with uniform flow."""
        graph = build_tick_graph()
        compiled = graph.compile()
        assert compiled is not None
