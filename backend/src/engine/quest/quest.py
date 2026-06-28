"""Quest Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.io.engine import QuestInput


def check_quests(input: QuestInput) -> list[str]:
    """检查任务完成 / Check quest completion. Mock."""
    return []
