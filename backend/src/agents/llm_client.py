"""LLM 客户端——多模型路由 + 多 provider 降级。per design/04-agent-layer.md §4 + design/06-llm-dev-guide.md §2.2."""

import asyncio
import logging
import os
from typing import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

from ..config import LLMConfig, LLMModelConfig

logger = logging.getLogger(__name__)


def _build_model(cfg: LLMModelConfig, base_url: str | None, api_key: str | None = None) -> BaseChatModel:
    """按 provider 构建 LangChain ChatModel."""
    return ChatOpenAI(
        model=cfg.model,
        temperature=cfg.temperature,
        base_url=base_url or "https://api.openai.com/v1",
        api_key=api_key or "sk-not-set",
    )


def _build_fallback_model(cfg: LLMModelConfig, fallback_base_url: str | None, api_key: str | None = None) -> BaseChatModel | None:
    """构建降级模型——支持切换到不同 provider."""
    if not cfg.fallback_model:
        return None
    # 如果有 Anthropic 降级 provider，用 Claude
    fallback_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if fallback_base_url and fallback_key:
        return ChatAnthropic(
            model=cfg.fallback_model,
            temperature=cfg.temperature,
            api_key=fallback_key,
        )
    # 退而用 OpenAI-compatible 降级模型
    return ChatOpenAI(
        model=cfg.fallback_model,
        temperature=cfg.temperature,
        base_url=fallback_base_url or "https://api.openai.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY", "sk-not-set"),
    )


class LLMClient:
    """多模型 LLM 客户端，支持结构化输出 + 重试 + 跨 provider 降级。

    Usage:
        client = LLMClient(config.llm)
        result = await client.call_structured(
            "dm_create", DMOutput,
            [SystemMessage(...), HumanMessage(...)],
            fallback=lambda: DMOutput(plot_brief="平静的一天..."),
        )
    """

    def __init__(self, config: LLMConfig):
        primary_key = os.environ.get("DEEPSEEK_API_KEY")
        primary_url = config.providers.primary.base_url
        fallback_key = os.environ.get("ANTHROPIC_API_KEY")
        fallback_url = config.providers.fallback.base_url if config.providers.fallback else None

        self._models: dict[str, BaseChatModel] = {}
        self._fallbacks: dict[str, BaseChatModel | None] = {}
        self._timeouts: dict[str, int] = {}
        self._retries: dict[str, int] = {}

        for purpose, cfg in [
            ("dm_create", config.dm_create),
            ("dm_narrate", config.dm_narrate),
            ("pc_decision", config.pc_decision),
            ("actor_decision", config.actor_decision),
            ("reflection", config.reflection),
        ]:
            self._models[purpose] = _build_model(cfg, primary_url, primary_key)
            self._fallbacks[purpose] = _build_fallback_model(cfg, fallback_url, fallback_key)
            self._timeouts[purpose] = cfg.timeout
            self._retries[purpose] = cfg.retries

    async def call(self, purpose: str, messages: list[BaseMessage]) -> str | None:
        """普通调用——带超时 + 重试 + 跨 provider 降级。per §4.1."""
        model = self._models[purpose]
        fallback = self._fallbacks.get(purpose)

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
            except asyncio.TimeoutError:
                logger.warning(f"LLM {purpose} timed out (attempt {attempt+1})")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"LLM {purpose} failed (attempt {attempt+1}): {e}")

            if attempt < self._retries[purpose]:
                await asyncio.sleep(0.5)
                continue

            # 所有重试失败，尝试降级模型
            if fallback and attempt == self._retries[purpose]:
                logger.warning(f"LLM {purpose} switching to fallback model")
                try:
                    response = await asyncio.wait_for(
                        fallback.ainvoke(messages),
                        timeout=self._timeouts[purpose],
                    )
                    content = response.content
                    if isinstance(content, list):
                        content = str(content[0]) if content else ""
                    return str(content)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"LLM {purpose} fallback also failed: {e}")

        logger.error(f"LLM {purpose} degraded after all retries and fallback")
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
        fallback_model = self._fallbacks.get(purpose)
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
                    f"Structured parse failed: {result.get('parsing_error')}"
                )
                if attempt < self._retries[purpose]:
                    await asyncio.sleep(0.5)
                    continue
            except asyncio.TimeoutError:
                logger.warning(f"LLM {purpose} structured timed out (attempt {attempt+1})")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"LLM {purpose} structured failed (attempt {attempt+1}): {e}")

            if attempt < self._retries[purpose]:
                await asyncio.sleep(0.5)
                continue

        # 降级到 fallback provider
        if fallback_model:
            logger.warning(f"LLM {purpose} structured switching to fallback model")
            try:
                fb_structured = fallback_model.with_structured_output(schema, include_raw=True)
                result = await asyncio.wait_for(
                    fb_structured.ainvoke(messages),
                    timeout=self._timeouts[purpose],
                )
                if result.get("parsed") is not None:
                    return result["parsed"]
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"LLM {purpose} structured fallback failed: {e}")

        logger.error(f"LLM {purpose} structured degraded")
        return fallback()
