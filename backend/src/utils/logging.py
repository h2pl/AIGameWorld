"""结构化日志辅助 / Structured logging helpers.

按 common-observability skill: 用 extra= 传结构化数据，支持 JSON 格式。
"""

import logging

logger = logging.getLogger(__name__)


def log_phase(phase: str, tick: int, elapsed: float | None = None, **extra) -> None:
    """记录 Graph Phase 执行 / Log Graph phase execution."""
    data = {"phase": phase, "tick": tick, **extra}
    if elapsed is not None:
        data["elapsed_ms"] = round(elapsed * 1000, 1)
    logger.info(f"[Phase] {phase} tick={tick}", extra=data)


def log_llm(purpose: str, action: str, elapsed: float, extra: dict | None = None) -> None:
    """记录 LLM 调用 / Log LLM call."""
    data = {"purpose": purpose, "action": action, "elapsed_ms": round(elapsed * 1000, 1)}
    if extra:
        data.update(extra)
    if action == "error":
        logger.error(f"[LLM] {purpose} failed", extra=data)
    else:
        logger.info(f"[LLM] {purpose} ok", extra=data)
