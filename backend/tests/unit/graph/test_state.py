"""Graph State 测试 / Graph State tests."""

from src.domain import Memory, Scene
from src.graph.state import OverallState, PcSubState, ReflectionSubState

# ══ OverallState 测试 / Main state tests ══


class TestOverallState:
    """根状态测试 / Root state tests."""

    def test_minimal_state(self):
        """最小状态构造 / Minimal state construction."""
        s: OverallState = {
            "tick": 0,
            "world_id": "",
            "scene": Scene(id=""),
            "scene_objects": [],
            "actions": [],
            "dm_record": None,
            "pc_decisions": [],
            "pcs": {},
            "actors": {},
        }
        assert s.get("tick") == 0


# ══ PcSubState 测试 ══


class TestPcSubState:
    """角色子图状态测试 / Character subgraph state tests."""

    def test_character_substate(self):
        """角色子状态构造 / Character subgraph state construction."""
        s: PcSubState = {
            "tick": 1,
            "plot_brief": "test",
            "scene": Scene(id=""),
            "scene_objects": [],
            "actions": [],
            "pc_decisions": [],
        }
        assert s["tick"] == 1
        assert s["plot_brief"] == "test"


# ══ ReflectionSubState 测试 ══


class TestReflectionSubState:
    """反思子图状态测试 / Reflection subgraph state tests."""

    def test_reflection_substate(self):
        """反思子状态构造 / Reflection subgraph state construction."""
        s: ReflectionSubState = {
            "tick": 5,
            "pc_id": "pc1",
            "memories": [Memory(id="m1", pc_id="pc1", content="m1", tick=1)],
            "tick_events": [],
            "reflected_pcs": [],
            "summary_compressed": False,
        }
        assert s["tick"] == 5
        assert len(s["memories"]) == 1
