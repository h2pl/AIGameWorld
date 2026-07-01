"""Quest Engine: 纯业务逻辑."""

import logging

from ...schemas.request import QuestRequest
from ...schemas.response import QuestResponse


def check_quests(req: QuestRequest) -> QuestResponse:
    logging.getLogger("aw.eng").info("[quest]")
    """检查任务完成. Mock. Phase 4 接入故事系统."""
    return QuestResponse(completed_ids=[q.get("id") for q in req.quests if q.get("completed")])
