"""Graph Subgraphs 测试 / Graph subgraph tests."""

# 测试框架 / Testing framework
import pytest

# State 定义 / State definitions
from src.graph.state import CharacterSubState, ReflectionSubState

# 子图 / Subgraphs
from src.graph.subgraphs.character_subgraph import character_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph


class TestCharacterSubgraph:
    """角色子图测试 / Character subgraph tests."""

    @pytest.mark.asyncio
    async def test_runs_without_crash(self):
        """空状态不崩溃 / Empty state does not crash."""
        state: CharacterSubState = {
            "tick": 0,
            "plot_brief": "",
            "character_actions": [],
        }
        result = await character_subgraph.ainvoke(state)
        assert "character_actions" in result


class TestReflectionSubgraph:
    """反思子图测试 / Reflection subgraph tests."""

    @pytest.mark.asyncio
    async def test_runs_without_crash(self):
        """空状态不崩溃 / Empty state does not crash."""
        state: ReflectionSubState = {
            "tick": 5,
            "character_id": "pc1",
            "memories": [{"text": "fought goblin"}],
            "events": [{"id": "e1"}],
            "reflected_characters": [],
            "summary_compressed": False,
        }
        result = await reflection_subgraph.ainvoke(state)
        assert "reflected_characters" in result
        assert "summary_compressed" in result
