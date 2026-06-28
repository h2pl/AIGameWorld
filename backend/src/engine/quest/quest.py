"""Quest Engine: 纯业务逻辑."""

from ...schemas.request import QuestRequest
from ...schemas.response import QuestResponse


def check_quests(req: QuestRequest) -> QuestResponse:
    """检查任务完成. Mock. Phase 4 接入."""
    return QuestResponse()
