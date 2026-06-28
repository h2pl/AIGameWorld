"""Actor Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.character import ActorDecideInput, ActorDecideOutput


def actor_decide(input: ActorDecideInput) -> ActorDecideOutput:
    """Phase 3: Actor 决策 / Actor decides action. Mock. M5 接入 LLM."""
    return ActorDecideOutput(
        character_id=input.get("actor_id", ""),
        type="idle",
        description="Going about daily business.",
    )
