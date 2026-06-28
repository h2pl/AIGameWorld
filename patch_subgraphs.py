"""批量覆盖 subgraph 文件，import 从 engine 改为 nodes。"""
import pathlib

base = pathlib.Path(r"E:\Projects\SimGameWorld\backend\src\graph\subgraphs")

files = {
    "dm_subgraph.py": '''"""DM Subgraphs: Phase 1 create + Phase 6 narrate / DM 子图。

子图以 subgraph-as-node 形式挂入主图, Schema 使用 plain dict;
Node 函数由 nodes/ 层提供, Service 由 engine/ 层提供。
"""
from langgraph.graph import StateGraph, END
from ...nodes.dm_nodes import dm_create_node, dm_narrate_node


def build_dm_create_subgraph() -> StateGraph:
    """Phase 1: DM 创造情境 / DM creates context."""
    graph = StateGraph(dict)
    graph.add_node("dm_create", dm_create_node)
    graph.set_entry_point("dm_create")
    graph.add_edge("dm_create", END)
    return graph


def build_dm_narrate_subgraph() -> StateGraph:
    """Phase 6: DM 叙事 / DM narrates."""
    graph = StateGraph(dict)
    graph.add_node("dm_narrate", dm_narrate_node)
    graph.set_entry_point("dm_narrate")
    graph.add_edge("dm_narrate", END)
    return graph


dm_create_subgraph = build_dm_create_subgraph().compile()
dm_narrate_subgraph = build_dm_narrate_subgraph().compile()
''',

    "world_subgraph.py": '''"""World Engine Subgraph: Phase 2 / 世界引擎子图。

子图以 subgraph-as-node 形式挂入主图, Schema 使用 plain dict;
Node 函数由 nodes/ 层提供, Service 由 engine/ 层提供。
"""
from langgraph.graph import StateGraph, END
from ...nodes.world_nodes import world_update_node


def build_world_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("world_update", world_update_node)
    graph.set_entry_point("world_update")
    graph.add_edge("world_update", END)
    return graph


world_subgraph = build_world_subgraph().compile()
''',

    "character_subgraph.py": '''"""Character Agent Subgraphs: PC + Actor / 角色智能体子图。

Node 函数由 nodes/ 层提供, Service 由 engine/ 层提供。
"""
from langgraph.graph import StateGraph, END
from ...nodes.character_nodes import pc_decide_node, actor_decide_node


def build_pc_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("pc_decide", pc_decide_node)
    graph.set_entry_point("pc_decide")
    graph.add_edge("pc_decide", END)
    return graph


def build_actor_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("actor_decide", actor_decide_node)
    graph.set_entry_point("actor_decide")
    graph.add_edge("actor_decide", END)
    return graph


pc_subgraph = build_pc_subgraph().compile()
actor_subgraph = build_actor_subgraph().compile()
''',

    "combat_subgraph.py": '''"""Combat Engine Subgraph: Phase 4 / 战斗引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.combat_nodes import combat_node


def build_combat_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("combat_resolve", combat_node)
    graph.set_entry_point("combat_resolve")
    graph.add_edge("combat_resolve", END)
    return graph


combat_subgraph = build_combat_subgraph().compile()
''',

    "dialogue_subgraph.py": '''"""Dialogue Engine Subgraph: Phase 4 / 对话引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.dialogue_nodes import dialogue_node


def build_dialogue_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("dialogue_process", dialogue_node)
    graph.set_entry_point("dialogue_process")
    graph.add_edge("dialogue_process", END)
    return graph


dialogue_subgraph = build_dialogue_subgraph().compile()
''',

    "exploration_subgraph.py": '''"""Exploration Engine Subgraph: Phase 4 / 探索引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.exploration_nodes import exploration_node


def build_exploration_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("exploration_process", exploration_node)
    graph.set_entry_point("exploration_process")
    graph.add_edge("exploration_process", END)
    return graph


exploration_subgraph = build_exploration_subgraph().compile()
''',

    "quest_subgraph.py": '''"""Quest Engine Subgraph: Phase 4 / 任务引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.quest_nodes import quest_node


def build_quest_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("quest_update", quest_node)
    graph.set_entry_point("quest_update")
    graph.add_edge("quest_update", END)
    return graph


quest_subgraph = build_quest_subgraph().compile()
''',

    "reflection_subgraph.py": '''"""Reflection Subgraph: Phase 7 / 角色反思子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.reflection_nodes import reflection_node


def build_reflection_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("reflect", reflection_node)
    graph.set_entry_point("reflect")
    graph.add_edge("reflect", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()
''',

    "summarizer_subgraph.py": '''"""Story Summarizer Subgraph: Phase 7 / 故事摘要子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.summarizer_nodes import summarizer_node


def build_summarizer_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("summarize", summarizer_node)
    graph.set_entry_point("summarize")
    graph.add_edge("summarize", END)
    return graph


summarizer_subgraph = build_summarizer_subgraph().compile()
''',
}

ok = 0
fail = 0
for name, content in files.items():
    path = base / name
    try:
        path.write_text(content, encoding="utf-8")
        ok += 1
    except Exception as e:
        print(f"FAIL {name}: {e}")
        fail += 1

print(f"\nDone: {ok} ok, {fail} fail")
