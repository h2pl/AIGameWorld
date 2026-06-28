"""Quest Engine: 纯业务逻辑."""

from ...schemas.request import QuestRequest


def check_quests(req: QuestRequest) -> list[str]:
    """检查任务完成. Mock."""
    return []
