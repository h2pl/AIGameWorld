"""Graph State 测试——OverallState / SubState 定义验证."""

from src.graph.state import CharacterSubState, EngineSubState, OverallState, ReflectionSubState

# ── OverallState 测试 / Main state tests ──


class TestOverallState:
    def test_minimal_state(self):
        s: OverallState = {
            "tick": 0,
            "world_id": "",
            "hints": [],
            "plot_brief": "",
            "scene": {},
            "scene_events": [],
            "character_actions": [],
            "engine_results": [],
            "combat_result": None,
            "state_diff": {},
            "narrative": "",
            "reflected_characters": [],
            "summary_compressed": False,
            "errors": [],
            "needs_reflection": False,
        }
        assert s["tick"] == 0

    def test_minimal_state_complete(self):
        """完整提供所有字段时 state 可用."""
        s: OverallState = {
            "tick": 0,
            "world_id": "",
            "hints": [],
            "plot_brief": "",
            "scene": {},
            "scene_events": [],
            "character_actions": [],
            "engine_results": [],
            "combat_result": None,
            "state_diff": {},
            "narrative": "",
            "reflected_characters": [],
            "summary_compressed": False,
            "errors": [],
            "needs_reflection": False,
        }
        assert s["tick"] == 0

    def test_scene_events_annotated_add(self):
        """Annotated[add] 标记的字段在 langgraph 中会累加."""
        # 这只是一个类型标记，运行时赋值仍然是普通 list
        s: OverallState = {
            "tick": 0,
            "world_id": "",
            "hints": [],
            "plot_brief": "",
            "scene": {},
            "scene_events": [{"e": 1}],
            "character_actions": [],
            "engine_results": [],
            "combat_result": None,
            "state_diff": {},
            "narrative": "",
            "reflected_characters": [],
            "summary_compressed": False,
            "errors": [],
            "needs_reflection": False,
        }
        assert len(s["scene_events"]) == 1

    def test_errors_annotated_add(self):
        s: OverallState = {
            "tick": 0,
            "world_id": "",
            "hints": [],
            "plot_brief": "",
            "scene": {},
            "scene_events": [],
            "character_actions": [],
            "engine_results": [],
            "combat_result": None,
            "state_diff": {},
            "narrative": "",
            "reflected_characters": [],
            "summary_compressed": False,
            "errors": ["error1", "error2"],
            "needs_reflection": False,
        }
        assert len(s["errors"]) == 2


# ── CharacterSubState 测试 ──
class TestCharacterSubState:
    def test_character_substate(self):
        s: CharacterSubState = {
            "tick": 1,
            "plot_brief": "test",
            "scene": {"scene_id": "tavern"},
            "character_actions": [],
        }
        assert s["tick"] == 1
        assert s["scene"]["scene_id"] == "tavern"


# ── EngineSubState 测试 ──
class TestEngineSubState:
    def test_engine_substate(self):
        s: EngineSubState = {
            "participants": ["a", "b"],
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
        assert len(s["participants"]) == 2


class TestReflectionSubState:
    def test_reflection_substate(self):
        s: ReflectionSubState = {
            "tick": 5,
            "character_id": "pc1",
            "memories": [{"text": "m1"}],
            "events": [],
            "reflected_characters": [],
            "summary_compressed": False,
        }
        assert s["tick"] == 5
        assert len(s["memories"]) == 1


# ── END / 结束
