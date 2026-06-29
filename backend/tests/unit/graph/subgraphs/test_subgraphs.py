"""Graph Subgraphs 测试——3 个子图编译并执行."""

import pytest

from src.graph.state import CharacterSubState, EngineSubState, ReflectionSubState
from src.graph.subgraphs.character_subgraph import character_subgraph
from src.graph.subgraphs.engine_subgraph import engine_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph


class TestCharacterSubgraph:
    @pytest.mark.asyncio
    async def test_runs_without_crash(self):
        state: CharacterSubState = {
            "tick": 0,
            "plot_brief": "",
            "scene_direction": {"featured_pcs": ["pc1"], "featured_actors": ["npc1"]},
            "character_actions": [],
        }
        result = await character_subgraph.ainvoke(state)
        assert "character_actions" in result
        actions = result["character_actions"]
        assert len(actions) >= 1

    @pytest.mark.asyncio
    async def test_no_actions_when_no_direction(self):
        state: CharacterSubState = {
            "tick": 0,
            "plot_brief": "",
            "scene_direction": {},
            "character_actions": [],
        }
        result = await character_subgraph.ainvoke(state)
        assert result["character_actions"] == []


class TestEngineSubgraph:
    @pytest.mark.asyncio
    async def test_runs_without_crash(self):
        state: EngineSubState = {
            "participants": [],
            "round": 1,
            "speaker": "",
            "target": "",
            "intent": "",
            "character_id": "",
            "action_type": "",
            "quests": [],
            "event_log": [],
            "engine_results": [],
            "combat_result": None,
        }
        result = await engine_subgraph.ainvoke(state)
        assert "engine_results" in result

    @pytest.mark.asyncio
    async def test_accumulates_results(self):
        """engine_results 标注了 add，多次调用应累加."""
        state: EngineSubState = {
            "participants": ["hero", "goblin"],
            "round": 1,
            "speaker": "pc1",
            "target": "npc1",
            "intent": "persuade",
            "character_id": "pc1",
            "action_type": "search",
            "quests": [{"id": "q1"}],
            "event_log": [],
            "engine_results": [],
            "combat_result": None,
        }
        result = await engine_subgraph.ainvoke(state)
        assert len(result["engine_results"]) >= 3  # combat + dialogue + exploration 至少


class TestReflectionSubgraph:
    @pytest.mark.asyncio
    async def test_runs_without_crash(self):
        state: ReflectionSubState = {
            "tick": 5,
            "character_id": "pc1",
            "memories": [{"text": "fought goblin"}],
            "events": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}, {"id": "e4"}],
            "reflected_characters": [],
            "summary_compressed": False,
        }
        result = await reflection_subgraph.ainvoke(state)
        assert "reflected_characters" in result
        assert "summary_compressed" in result
