"""DM Agent 子图 / DM Agent Subgraph.
Phase 1（创造情境）/ Phase 1 (create context).
Phase 6（渲染叙事）/ Phase 6 (narrate).

Mock: 返回固定 plot_brief 和空指令 / Returns fixed plot_brief and empty instructions.
后续 M4 接入 LLM / M4 connects to LLM.
"""

from typing import TypedDict, Any


class DMSubState(TypedDict):
    """DM 子图状态 / DM subgraph state."""
    world_snapshot: dict[str, Any]
    story_arcs: list[dict[str, Any]]
    story_hooks: list[dict[str, Any]]
    dm_memory: dict[str, Any]
    plot_brief: str
    instructions_out: list[dict[str, Any]]
    scene_direction: dict[str, Any]
    narrative_out: str
    execution_results: dict[str, Any]  # Phase 6 独有 / Phase 6 only


def dm_create_context(state: dict[str, Any]) -> DMSubState:
    """Phase 1: DM 创造情境 / DM creates context.
    
    Mock: 返回预设的剧情梗概 / Returns preset plot brief.
    """
    return DMSubState(
        world_snapshot=state.get("world_snapshot", {}),
        story_arcs=state.get("story_arcs", []),
        story_hooks=state.get("story_hooks", []),
        dm_memory=state.get("dm_memory", {}),
        plot_brief=state.get("plot_brief", "The adventure continues..."),
        instructions_out=[],  # 空指令 / Empty instructions
        scene_direction={"featured_pcs": [], "featured_actors": []},
        narrative_out="",
        execution_results={},
    )


def dm_narrate(state: dict[str, Any]) -> DMSubState:
    """Phase 6: DM 基于结果渲染叙事 / DM narrates based on results.
    
    Mock: 简单拼接叙事文本 / Simple narrative concatenation.
    """
    plot = state.get("plot_brief", "")
    actions = state.get("execution_results", {}).get("character_actions", [])
    narrative = f"[DM Narrative] {plot} Characters acted: {len(actions)}"
    return DMSubState(
        world_snapshot=state.get("world_snapshot", {}),
        story_arcs=state.get("story_arcs", []),
        story_hooks=state.get("story_hooks", []),
        dm_memory=state.get("dm_memory", {}),
        plot_brief=plot,
        instructions_out=[],
        scene_direction={},
        narrative_out=narrative,
        execution_results=state.get("execution_results", {}),
    )
