"""Graph Subgraphs 测试——对齐当前子图结构。"""

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.subgraphs.pc_subgraph import pc_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph


class TestCharacterSubgraph:
    """角色子图测试 / Character subgraph tests."""

    @pytest.mark.asyncio
    async def test_pc_subgraph_runs_decide_act_chain(self):
        """角色子图执行 decide → act 两阶段链路（场景信息已由 scene_service 提前构建好，不区分 PC）/ Subgraph runs decide → act (scene info precomputed by scene_service, not per-PC)."""
        scene_info = {"scene": {"id": "tavern"}, "scene_objects": []}
        pc_state_map = {"pc-1": {"name": "pc-1", "role": "", "position_x": 0, "position_y": 0}}
        state = {
            "tick": 1,
            "world_id": "world-1",
            "plot_brief": "酒馆起争执",
            "hints": [],
            "scene_id": "tavern",
            "pc_decisions": [],
            "scene_info": scene_info,
            "pc_state_map": pc_state_map,
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
        assert result["scene_info"] == scene_info
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
