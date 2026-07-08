"""Quest Engine: 纯业务逻辑."""

from ...utils.logging import get_logger


def check_quests(quests: list[dict], completed_ids: list[str] | None = None) -> list[str]:
    """检查任务完成. Mock. Phase 4 接入故事系统."""
    get_logger(__name__).info("[engine]")
    completed = completed_ids or []
    for q in quests:
        if isinstance(q, dict) and q.get("completed"):
            completed.append(q.get("id", ""))
    return completed
