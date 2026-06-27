"""Wrapper: 主图 ↔ 子图 State 转换 / Main graph ↔ subgraph state conversion.

每个子图有自己的 State Schema，Wrapper 负责：
1. 从主图 OverallState 提取子图需要的字段 / Extract subgraph fields from OverallState
2. 把子图输出映射回主图字段 / Map subgraph output back to OverallState fields
"""

from typing import Any


# ============================================================
# DM Subgraph Wrappers (Phase 1 Create + Phase 6 Narrate)
# ============================================================

def wrap_dm_create_input(state: dict[str, Any]) -> dict[str, Any]:
    """主图 → DM 子图（Phase 1 创造情境）/ Main graph → DM subgraph (Phase 1 create)."""
    return {
        "tick": state.get("tick", 0),
        "plot_brief": state.get("plot_brief", ""),
    }


def unwrap_dm_create_output(result: dict[str, Any]) -> dict[str, Any]:
    """DM 子图 → 主图（Phase 1）/ DM subgraph → main graph (Phase 1)."""
    return {
        "dm_instructions": result.get("instructions_out", []),
        "plot_brief": result.get("plot_brief", ""),
        "scene_direction": result.get("scene_direction", {}),
    }


def wrap_dm_narrate_input(state: dict[str, Any]) -> dict[str, Any]:
    """主图 → DM 子图（Phase 6 叙事）/ Main graph → DM subgraph (Phase 6 narrate)."""
    return {
        "tick": state.get("tick", 0),
        "plot_brief": state.get("plot_brief", ""),
        "character_actions": state.get("character_actions", []),
    }


def unwrap_dm_narrate_output(result: dict[str, Any]) -> dict[str, Any]:
    """DM 子图 → 主图（Phase 6）/ DM subgraph → main graph (Phase 6)."""
    return {"narrative": result.get("narrative_out", "")}


# ============================================================
# WorldEngine Subgraph Wrappers (Phase 2)
# ============================================================

def wrap_world_engine_input(state: dict[str, Any]) -> dict[str, Any]:
    """主图 → WorldEngine 子图 / Main graph → WorldEngine subgraph."""
    return {
        "tick": state.get("tick", 0),
        "dm_instructions": state.get("dm_instructions", []),
    }


def unwrap_world_engine_output(result: dict[str, Any]) -> dict[str, Any]:
    """WorldEngine 子图 → 主图 / WorldEngine subgraph → main graph."""
    return {"world_events": result.get("events_out", [])}
