"""Combat Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.engine import CombatInput, CombatOutput


def resolve_combat(input: CombatInput) -> CombatOutput | None:
    """战斗裁决 / Combat resolution. Mock. M6 接入 DndRules."""
    return None
