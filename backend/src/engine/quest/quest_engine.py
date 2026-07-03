"""Quest Engine: 纯业务逻辑."""

from ...schemas.request import QuestRequest
from ...schemas.response import QuestResponse
from ...utils.logging import get_logger


def check_quests(req: QuestRequest) -> QuestResponse:
    get_logger(__name__).info("[engine]")
    """检查任务完成. Mock. Phase 4 接入故事系统."""
    return QuestResponse(completed_ids=[q.get("id") for q in req.quests if q.get("completed")])
