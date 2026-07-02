"""Graph Subgraphs 测试——对齐当前子图结构。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.graph.subgraphs.character_subgraph import character_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph
from src.schemas.response import SceneObservation


class TestCharacterSubgraph:
    """角色子图测试 / Character subgraph tests."""

    @pytest.mark.asyncio
    async def test_character_subgraph_runs_observe_decide_act_chain(self):
        """角色子图执行 observe → decide → act 三阶段链路 / Subgraph runs three-phase chain."""
        state = {
            "tick": 1,
            "world_id": "world-1",
            "tick_message_id": "msg-1",
            "plot_brief": "酒馆起争执",
            "hints": [],
            "scene_id": "tavern",
            "character_actions": [],
            "scene_observations": [],
        }
        # 场景内唯一一个 PC / The only PC in the scene
        pc = SimpleNamespace(id="pc-1", scene_id="tavern")
        char_repo = AsyncMock()
        char_repo.load_pcs = AsyncMock(return_value=[pc])
        config = {"configurable": {"repos": {"char": char_repo}}}

        observation = SceneObservation(pc_id="pc-1")
        action = {"pc_id": "pc-1", "type": "talk", "description": "先问话"}
        with (
            patch(
                "src.services.character_service.observation_engine.observe_scene",
                AsyncMock(return_value=observation),
            ),
            patch(
                "src.services.character_service.decision_engine.decide",
                AsyncMock(return_value=action),
            ),
            patch(
                "src.services.character_service.talk_engine.process_talk_action",
                AsyncMock(),
            ),
            patch(
                "src.services.character_service.exploration_engine.process_explore_action",
                AsyncMock(),
            ),
        ):
            result = await character_subgraph.ainvoke(state, config=config)
        assert result["scene_observations"] == [observation.model_dump()]
        assert result["character_actions"] == [action]


class TestReflectionSubgraph:
    """反思子图测试 / Reflection subgraph tests."""

    @pytest.mark.asyncio
    async def test_reflection_subgraph_runs_single_node(self):
        """反思子图执行单节点反思 / Reflection subgraph runs single reflection node."""
        state = {
            "tick": 5,
            "character_id": "pc-1",
            "memories": [],
            "tick_events": [],
            "reflected_characters": [],
            "summary_compressed": False,
        }
        with patch("src.services.reflection_service.get_repo", side_effect=[None, None]):
            result = await reflection_subgraph.ainvoke(state)
        # ainvoke 返回合并后的完整状态，而不仅是节点的返回值 / ainvoke returns the merged full state
        assert result["reflected_characters"] == []
