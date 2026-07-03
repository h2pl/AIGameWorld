"""共享辅助函数 / Shared helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .logging import get_logger

if TYPE_CHECKING:
    from langchain_core.runnables.config import RunnableConfig

logger = get_logger(__name__)


def get_llm(config: RunnableConfig | None):
    """从 config 取 LLM 客户端."""
    if config and "configurable" in config:
        llm = config["configurable"].get("llm")
        if llm is None:
            logger.warning("[utils] LLM not available in config")
        return llm
    logger.warning("[utils] No config provided, LLM unavailable")
    return None


def get_repos(config: RunnableConfig | None) -> dict | None:
    """从 config 取完整的 Repo 字典."""
    if config and "configurable" in config:
        repos = config["configurable"].get("repos")
        if repos is None:
            logger.debug("[utils] No repos in config")
        return repos
    logger.debug("[utils] No config provided, repos unavailable")
    return None


def get_repo(config: RunnableConfig | None, name: str):
    """按名取单个 Repo."""
    repos = get_repos(config)
    if repos is None:
        logger.warning("[utils] Repo '%s' not found, repos unavailable", name)
        return None
    repo = repos.get(name)
    if repo is None:
        logger.warning("[utils] Repo '%s' not found in config", name)
    return repo


def is_mock(config: RunnableConfig | None) -> bool:
    """是否 mock 模式."""
    if config and "configurable" in config:
        return config["configurable"].get("mock", False)
    return False
