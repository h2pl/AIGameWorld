"""DM Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.dm import DMCreateInput, DMCreateOutput, DMNarrateInput, DMNarrateOutput


def dm_create(input: DMCreateInput) -> DMCreateOutput:
    """Phase 1: DM 创造情境 / DM creates context. Mock. M4 接入 LLM."""
    return DMCreateOutput(
        plot_brief=f"[Tick {input.tick}] The adventure continues in the Forgotten Realms.",
    )


def dm_narrate(input: DMNarrateInput) -> DMNarrateOutput:
    """Phase 6: DM 叙事 / DM narrates. Mock. M4 接入 LLM."""
    return DMNarrateOutput(
        narrative_out=f"[DM Narrative] {input.plot_brief} (Actions: {len(input.character_actions)})",
    )
