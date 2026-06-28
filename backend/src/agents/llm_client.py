"""LLM 客户端——多模型路由 + 超时降级。per design/04-agent-layer.md §4 + design/06-llm-dev-guide.md §2.2."""

import asyncio
import logging
from typing import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """多模型 LLM 客户端，支持结构化输出 + 重试 + 降级。

    Usage:
        client = LLMClient(config.llm)
        result = await client.call_structured(
            "dm_create", DMOutput,
            [SystemMessage(...), HumanMessage(...)],
            fallback=lambda: DMOutput(plot_brief="平静的一天..."),
        )
    """

    def __init__(self, config: LLMConfig):
        self._models: dict[str, BaseChatModel] = {}
        self._timeouts: dict[str, int] = {}
        self._retries: dict[str, int] = {}

        for purpose, cfg in [
            ("dm_create", config.dm_create),
            ("dm_narrate", config.dm_narrate),
            ("pc_decision", config.pc_decision),
            ("actor_decision", config.actor_decision),
            ("reflection", config.reflection),
        ]:
            self._models[purpose] = ChatOpenAI(
                model=cfg.model,
                temperature=cfg.temperature,
                base_url=config.providers.primary.base_url or "https://api.openai.com/v1",
            )
            self._timeouts[purpose] = cfg.timeout
            self._retries[purpose] = cfg.retries

    async def call(self, purpose: str, messages: list[BaseMessage]) -> str | None:
        """普通调用——带超时 + 重试 + 降级。per §4.1."""
        model = self._models[purpose]
        for attempt in range(self._retries[purpose] + 1):
            try:
                response = await asyncio.wait_for(
                    model.ainvoke(messages),
                    timeout=self._timeouts[purpose],
                )
                content = response.content
                if isinstance(content, list):
                    content = str(content[0]) if content else ""
                return str(content)
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"LLM {purpose} failed (attempt {attempt+1}): {e}")
                if attempt < self._retries[purpose]:
                    await asyncio.sleep(0.5)
                    continue
        logger.error(f"LLM {purpose} degraded after retries")
        return None

    async def call_structured(
        self,
        purpose: str,
        schema: type[BaseModel],
        messages: list[BaseMessage],
        fallback: Callable[[], BaseModel],
    ) -> BaseModel:
        """结构化 LLM 调用——with_structured_output，失败自动降级。per §2.2."""
        model = self._models[purpose]
        structured_model = model.with_structured_output(schema, include_raw=True)

        for attempt in range(self._retries[purpose] + 1):
            try:
                result = await asyncio.wait_for(
                    structured_model.ainvoke(messages),
                    timeout=self._timeouts[purpose],
                )
                if result.get("parsed") is not None:
                    return result["parsed"]
                logger.warning(
                    f"Structured parse failed after retries: {result.get('parsing_error')}"
                )
                return fallback()
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"LLM {purpose} structured failed (attempt {attempt+1}): {e}")
                if attempt < self._retries[purpose]:
                    await asyncio.sleep(0.5)
                    continue
        logger.error(f"LLM {purpose} structured degraded")
        return fallback()
