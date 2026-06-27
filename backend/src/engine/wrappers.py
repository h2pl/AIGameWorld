"""Wrapper: 主图 ↔ 子图 State 转换 / Main graph ↔ subgraph state conversion.

基于 design/03-orchestration-layer.md §4.3 / Based on orchestration layer design.
字段同名自动透传，不同则手动映射。
Fields with same name auto-pass-through; different fields mapped manually.
"""

from typing import Any


def wrap_dm_input(state: dict[str, Any]) -> dict[str, Any]:
    """主图 → DM 子图 / Main graph → DM subgraph.
    
    Args:
        state: OverallState
    
    Returns:
        dict: DMSubState 输入 / DMSubState input
    """
    return {
        "world_snapshot": state.get("world_snapshot", {}),
        "story_arcs": state.get("story_arcs", []),
        "story_hooks": state.get("story_hooks", []),
        "dm_memory": state.get("dm_memory", {}),
        "plot_brief": state.get("plot_brief", ""),
    }


def unwrap_dm_output(result: dict[str, Any]) -> dict[str, Any]:
    """DM 子图 → 主图 / DM subgraph → main graph.
    
    Args:
        result: DMSubState output
        
    Returns:
        dict: OverallState 更新 / OverallState update
    """
    return {
        "dm_instructions": result.get("instructions_out", []),
        "plot_brief": result.get("plot_brief", ""),
        "scene_direction": result.get("scene_direction", {}),
    }


def wrap_world_engine_input(state: dict[str, Any]) -> dict[str, Any]:
    """主图 → WorldEngine 子图 / Main graph → WorldEngine subgraph."""
    return {
        "instructions": state.get("dm_instructions", []),
        "world_snapshot": state.get("world_snapshot", {}),
    }


def unwrap_world_engine_output(result: dict[str, Any]) -> dict[str, Any]:
    """WorldEngine 子图 → 主图 / WorldEngine subgraph → main graph."""
    return {"world_events": result.get("events_out", [])}


def wrap_pc_input(state: dict[str, Any], pc_id: str) -> dict[str, Any]:
    """主图 → PC 子图 / Main graph → PC subgraph (per PC)."""
    return {
        "pc_id": pc_id,
        "world_snapshot": state.get("world_snapshot", {}),
        "plot_brief": state.get("plot_brief", ""),
        "memory_retrieved": state.get("memory_retrieved", {}),
    }


def wrap_actor_input(state: dict[str, Any], actor_id: str) -> dict[str, Any]:
    """主图 → Actor 子图 / Main graph → Actor subgraph (per actor)."""
    return {
        "actor_id": actor_id,
        "world_snapshot": state.get("world_snapshot", {}),
        "plot_brief": state.get("plot_brief", ""),
        "motivation_injected": state.get("motivation_injected", ""),
        "memory_retrieved": state.get("memory_retrieved", {}),
    }


def unwrap_character_output(result: dict[str, Any]) -> dict[str, Any]:
    """PC/Actor 子图 → 主图 / Character subgraph → main graph."""
    return {"character_actions": [result.get("action_out", {})]}


def wrap_dm_narrate_input(state: dict[str, Any]) -> dict[str, Any]:
    """主图 → DM 叙事子图（Phase 6）/ Main graph → DM narration (Phase 6)."""
    return {
        "plot_brief": state.get("plot_brief", ""),
        "world_snapshot": state.get("world_snapshot", {}),
        "execution_results": {
            "character_actions": state.get("character_actions", []),
            "engine_results": state.get("engine_results", []),
            "combat_result": state.get("combat_result"),
        },
    }


def unwrap_dm_narrate_output(result: dict[str, Any]) -> dict[str, Any]:
    """DM 叙事子图 → 主图 / DM narration subgraph → main graph."""
    return {
        "narrative": result.get("narrative_out", ""),
    }
