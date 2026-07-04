"""TickGraph 主图测试——对齐当前主图结构。"""


from langgraph.checkpoint.memory import MemorySaver

from src.graph.graph import build_tick_graph


def _graph_input(**overrides):
    return {
        "tick": 5,
        "world_id": "world-1",
        "scene_info": {},
        "pending_actions": [],
        "hints": [],
        "plot_brief": "",
        "scene_id": "scene-1",
        "pc_decisions": [],
        "narrative": "",
        **overrides,
    }


def test_build_graph_returns_state_graph():
    assert build_tick_graph() is not None


def test_graph_can_compile():
    app = build_tick_graph().compile(checkpointer=MemorySaver())
    assert app is not None
