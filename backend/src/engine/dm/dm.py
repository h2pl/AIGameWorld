"""DM Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.dm import DMCreateInput, DMCreateOutput, DMNarrateInput, DMNarrateOutput


def dm_create(input: DMCreateInput) -> DMCreateOutput:
    """Phase 1: DM 创造情境 / DM creates context. Mock. M4 接入 LLM."""
    tick = input.get("tick", 0)
    return DMCreateOutput(
        instructions_out=[],
        plot_brief=f"[Tick {tick}] The adventure continues in the Forgotten Realms.",
        scene_direction={"featured_pcs": [], "featured_actors": []},
    )


def dm_narrate(input: DMNarrateInput) -> DMNarrateOutput:
    """Phase 6: DM 叙事 / DM narrates. Mock. M4 接入 LLM."""
    plot = input.get("plot_brief", "")
    actions = input.get("character_actions", [])
    return DMNarrateOutput(
        narrative_out=f"[DM Narrative] {plot} (Actions: {len(actions)})",
    )
