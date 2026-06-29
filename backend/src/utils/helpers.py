"""共享辅助函数 / Shared helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.runnables.config import RunnableConfig


def get_llm(config: RunnableConfig | None):
    """从 config 取 LLM 客户端 / Extract LLM client from config."""
    if config and "configurable" in config:
        return config["configurable"].get("llm")
    return None


def get_repos(config: RunnableConfig | None) -> dict | None:
    """从 config 取完整的 Repo 字典 / Extract complete repo dict from config."""
    if config and "configurable" in config:
        return config["configurable"].get("repos")
    return None


def get_repo(config: RunnableConfig | None, name: str):
    """按名取单个 Repo / Get single repo by name (e.g. 'story', 'char', 'memory')."""
    repos = get_repos(config)
    return repos.get(name) if repos else None
