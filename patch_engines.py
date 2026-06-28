"""批量覆盖 engine 文件，改为 Service 纯函数。"""
import pathlib

base = pathlib.Path(r"E:\Projects\SimGameWorld\backend\src\engine")

files = {
    "dm/dm.py": '''"""DM Service: 纯业务逻辑 / Pure business logic (Service layer).

Service 层职责: 封装业务逻辑 / LLM 调用 / Prompt 构造 / 工具协调 / 不依赖 LangGraph
"""

from typing import TypedDict, Any


class DMSubState(TypedDict):
    """DM Service 内部数据契约 / DM service internal data contract."""
    tick: int
    plot_brief: str
    instructions_out: list[dict[str, Any]]
    scene_direction: dict[str, Any]
    narrative_out: str
    character_actions: list[dict[str, Any]]


def dm_create(state: DMSubState) -> dict:
    """Phase 1: DM 创造情境 / DM creates context. Mock. M4 接入 LLM."""
    tick = state.get("tick", 0)
    return {
        "plot_brief": f"[Tick {tick}] The adventure continues in the Forgotten Realms.",
        "instructions_out": [],
        "scene_direction": {"featured_pcs": [], "featured_actors": []},
    }


def dm_narrate(state: DMSubState) -> dict:
    """Phase 6: DM 叙事 / DM narrates. Mock. M4 接入 LLM."""
    plot = state.get("plot_brief", "")
    actions = state.get("character_actions", [])
    narrative = f"[DM Narrative] {plot} (Actions: {len(actions)})"
    return {"narrative_out": narrative}
''',

    "world/world.py": '''"""World Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class WorldEngineSubState(TypedDict):
    """WorldEngine Service 内部数据契约 / WorldEngine service internal data contract."""
    tick: int
    dm_instructions: list[dict[str, Any]]
    events_out: list[dict[str, Any]]


def execute_instructions(state: WorldEngineSubState) -> dict:
    """执行 DM 指令 / Execute DM instructions. Mock. M6 接入场景实例化."""
    return {"events_out": []}
''',

    "combat/combat.py": '''"""Combat Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class CombatSubState(TypedDict):
    """Combat Service 内部数据契约 / Combat service internal data contract."""
    participants: list[str]
    round: int
    result: dict[str, Any] | None


def resolve_combat(participants: list[str], round: int) -> dict[str, Any] | None:
    """战斗裁决 / Combat resolution. Mock. M6 接入 DndRules."""
    return None
''',

    "dialogue/dialogue.py": '''"""Dialogue Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class DialogueSubState(TypedDict):
    """Dialogue Service 内部数据契约 / Dialogue service internal data contract."""
    speaker: str
    target: str
    intent: str
    check_result: dict[str, Any]


def resolve_dialogue(speaker: str, target: str, intent: str) -> dict[str, Any]:
    """对话检定 / Dialogue check. Mock."""
    return {}
''',

    "exploration/exploration.py": '''"""Exploration Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class ExplorationSubState(TypedDict):
    """Exploration Service 内部数据契约 / Exploration service internal data contract."""
    character_id: str
    action_type: str
    check_result: dict[str, Any]


def resolve_exploration(character_id: str, action_type: str) -> dict[str, Any]:
    """探索检定 / Exploration check. Mock."""
    return {}
''',

    "quest/quest.py": '''"""Quest Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class QuestSubState(TypedDict):
    """Quest Service 内部数据契约 / Quest service internal data contract."""
    quests: list[dict[str, Any]]
    event_log: list[dict[str, Any]]
    completed_quests: list[str]


def check_quests(quests: list[dict[str, Any]], event_log: list[dict[str, Any]]) -> list[str]:
    """检查任务完成 / Check quest completion. Mock."""
    return []
''',

    "reflection/reflection.py": '''"""Reflection Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class ReflectionSubState(TypedDict):
    """Reflection Service 内部数据契约 / Reflection service internal data contract."""
    character_id: str
    memories: list[dict[str, Any]]
    insight_out: str


def reflect(character_id: str, memories: list[dict[str, Any]]) -> str:
    """角色反思 / Character reflection. Mock."""
    return ""
''',

    "summarizer/summarizer.py": '''"""Summarizer Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class SummarizerSubState(TypedDict):
    """Summarizer Service 内部数据契约 / Summarizer service internal data contract."""
    events: list[dict[str, Any]]
    tick: int
    summary: str


def summarize(events: list[dict[str, Any]], tick: int) -> str:
    """压缩事件 / Compress events. Mock."""
    return ""
''',

    "character/pc_decide.py": '''"""PC Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class PCSubState(TypedDict):
    """PC Service 内部数据契约 / PC service internal data contract."""
    tick: int
    pc_id: str
    plot_brief: str
    character_state: dict[str, Any]
    action: dict[str, Any]


def pc_decide(pc_id: str, plot_brief: str, tick: int) -> dict[str, Any]:
    """Phase 3: PC 决策 / PC decides action. Mock. M5 接入 LLM."""
    return {
        "character_id": pc_id,
        "type": "explore",
        "description": "Looking around the area.",
    }
''',

    "character/actor_decide.py": '''"""Actor Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class ActorSubState(TypedDict):
    """Actor Service 内部数据契约 / Actor service internal data contract."""
    tick: int
    actor_id: str
    plot_brief: str
    character_state: dict[str, Any]
    action: dict[str, Any]


def actor_decide(actor_id: str, plot_brief: str, tick: int) -> dict[str, Any]:
    """Phase 3: Actor 决策 / Actor decides action. Mock. M5 接入 LLM."""
    return {
        "character_id": actor_id,
        "type": "idle",
        "description": "Going about daily business.",
    }
''',
}

ok = 0
fail = 0
for name, content in files.items():
    path = base / name
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        ok += 1
    except Exception as e:
        print(f"FAIL {name}: {e}")
        fail += 1

print(f"Done: {ok} ok, {fail} fail")
