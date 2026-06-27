"""CharacterAgent 子图 / Character Agent Subgraph.
Phase 3: PC/Actor 决策（Send fan-out 并行）/ PC/Actor decisions (parallel fan-out).
Mock: 空行动. 后续 M5 接入 / Mock: empty actions. M5 integration.
"""

from typing import TypedDict, Any


class PCSubState(TypedDict):
    """PC Agent 子图状态 / PC Agent subgraph state."""
    pc_id: str
    world_snapshot: dict[str, Any]
    plot_brief: str
    character_arc: dict[str, Any]
    long_term_goal: str
    values: list[str]
    memory_retrieved: dict[str, Any]
    action_out: dict[str, Any] | None  # 输出的行动 / Output action


class ActorSubState(TypedDict):
    """Actor Agent 子图状态 / Actor Agent subgraph state."""
    actor_id: str
    world_snapshot: dict[str, Any]
    plot_brief: str
    motivation_injected: str
    memory_retrieved: dict[str, Any]
    action_out: dict[str, Any] | None  # 输出的行动 / Output action


def pc_decide(state: dict[str, Any]) -> PCSubState:
    """PC 深层决策 / PC deep decision.
    
    Mock: 返回空行动.
    """
    return PCSubState(
        pc_id=state.get("pc_id", ""),
        world_snapshot=state.get("world_snapshot", {}),
        plot_brief=state.get("plot_brief", ""),
        character_arc=state.get("character_arc", {}),
        long_term_goal=state.get("long_term_goal", ""),
        values=state.get("values", []),
        memory_retrieved=state.get("memory_retrieved", {}),
        action_out=None,  # 空行动 / No action yet
    )


def actor_decide(state: dict[str, Any]) -> ActorSubState:
    """Actor 浅层决策 / Actor shallow decision.
    
    Mock: 返回空行动.
    """
    return ActorSubState(
        actor_id=state.get("actor_id", ""),
        world_snapshot=state.get("world_snapshot", {}),
        plot_brief=state.get("plot_brief", ""),
        motivation_injected=state.get("motivation_injected", ""),
        memory_retrieved=state.get("memory_retrieved", {}),
        action_out=None,  # 空行动 / No action yet
    )
