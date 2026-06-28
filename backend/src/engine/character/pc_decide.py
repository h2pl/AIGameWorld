"""PC Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.character import PCDecideInput, PCDecideOutput


def pc_decide(input: PCDecideInput) -> PCDecideOutput:
    """Phase 3: PC 决策 / PC decides action. Mock. M5 接入 LLM."""
    return PCDecideOutput(
        character_id=input.pc_id,
        type="explore",
        description="Looking around the area.",
    )
