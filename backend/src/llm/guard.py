"""LLM 输出护栏——校验 + 降级 / Output guardrails — validate + fallback."""

import logging
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def validate_or_fallback(
    result: BaseModel | None,
    expected_type: type[BaseModel],
    fallback: BaseModel,
    source: str = "llm",
) -> BaseModel:
    """校验 LLM 输出，失败则降级 / Validate LLM output, fallback on failure.

    Args:
        result: LLM 返回的 Pydantic 模型
        expected_type: 期望的类型
        fallback: 降级默认值
        source: 调用源名称，用于日志

    Returns:
        校验通过的结果或降级值
    """
    if result is None:
        logger.warning(f"[{source}] LLM returned None, using fallback")
        return fallback

    if not isinstance(result, expected_type):
        logger.warning(
            f"[{source}] Expected {expected_type.__name__}, got {type(result).__name__}"
        )
        return fallback

    return result


def validate_field_non_empty(
    data: dict[str, Any],
    fields: list[str],
    source: str = "llm",
) -> list[str]:
    """校验必填字段非空 / Validate required fields are non-empty.

    Returns:
        缺失或为空的字段名列表
    """
    missing = []
    for f in fields:
        val = data.get(f)
        if val is None or (isinstance(val, (str, list, dict)) and not val):
            missing.append(f)
    if missing:
        logger.warning(f"[{source}] Empty required fields: {missing}")
    return missing
