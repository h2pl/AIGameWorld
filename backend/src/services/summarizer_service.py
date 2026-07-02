"""Summarizer service compatibility wrapper / 摘要服务兼容包装。"""

from langchain_core.runnables.config import RunnableConfig


async def summarize(state: dict, config: RunnableConfig = None) -> dict:
    """Return minimal summarizer-compatible result / 返回最小兼容摘要结果。"""
    return {
        "summary_compressed": False,
        "tick_events": state.get("tick_events", state.get("events", [])),
    }
