"""DM Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.dm import DMCreateInput, DMCreateOutput, DMNarrateInput, DMNarrateOutput
from ...models.instruction import DMInstruction


def dm_create(input: DMCreateInput) -> DMCreateOutput:
    """Phase 1: DM 创造情境 / DM creates context.

    ① Input → Domain Model  ② 业务逻辑  ③ Domain → Output
    Mock. M4 接入 LLM.
    """
    dm = DMInstruction.from_input(input)             # ① Input → Domain
    dm.plot_brief = f"[Tick {input.tick}] The adventure continues..."  # ②
    return dm.to_output()                            # ③ Domain → Output


def dm_narrate(input: DMNarrateInput) -> DMNarrateOutput:
    """Phase 6: DM 叙事 / DM narrates. Mock. M4 接入 LLM."""
    return DMNarrateOutput(
        narrative_out=f"[DM Narrative] {input.plot_brief} (Actions: {len(input.character_actions)})",
    )
