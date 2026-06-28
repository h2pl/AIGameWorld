"""LLM 客户端——多模型路由 + requests 直连（httpx 与 Zen Proxy 不兼容）."""

import asyncio
import json
import logging
import os
from typing import Callable

import requests
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from pydantic import BaseModel

from ..config import LLMConfig, LLMModelConfig

logger = logging.getLogger(__name__)


class RequestsChatModel(BaseChatModel):
    """用 requests 替代 httpx 的 ChatModel——解决 Zen Proxy 502 问题."""

    model: str = ""
    temperature: float = 0.7
    base_url: str = ""

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        raise NotImplementedError("Use async version")

    async def _agenerate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        _role_map = {"human": "user", "ai": "assistant"}
        payload = {
            "model": self.model,
            "messages": [{"role": _role_map.get(m.type, m.type), "content": m.content} for m in messages],
            "temperature": self.temperature,
        }
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout if hasattr(self, 'timeout') else 30,
            ),
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    @property
    def _llm_type(self) -> str:
        return "requests-chat"


def _build_model(cfg: LLMModelConfig, base_url: str | None, api_key: str | None = None) -> BaseChatModel:
    """构建基于 requests 的 ChatModel."""
    return RequestsChatModel(
        model=cfg.model,
        temperature=cfg.temperature,
        base_url=(base_url or "https://api.openai.com/v1").rstrip("/"),
    )


def _build_fallback_model(cfg: LLMModelConfig, fallback_base_url: str | None, api_key: str | None = None) -> BaseChatModel | None:
    """构建降级模型."""
    if not cfg.fallback_model:
        return None
    return RequestsChatModel(
        model=cfg.fallback_model,
        temperature=cfg.temperature,
        base_url=(fallback_base_url or "https://api.openai.com/v1").rstrip("/"),
    )


class LLMClient:
    """多模型 LLM 客户端."""

    def __init__(self, config: LLMConfig):
        primary_key = os.environ.get("DEEPSEEK_API_KEY")
        primary_url = config.providers.primary.base_url
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
            model_url = cfg.base_url or primary_url
            self._models[purpose] = _build_model(cfg, model_url, primary_key)
            self._fallbacks[purpose] = _build_fallback_model(cfg, fallback_url)
            self._timeouts[purpose] = cfg.timeout
            self._retries[purpose] = cfg.retries

    async def call(self, purpose: str, messages: list[BaseMessage]) -> str | None:
        model = self._models[purpose]
        for attempt in range(self._retries[purpose] + 1):
            try:
                result = await asyncio.wait_for(
                    model._agenerate(messages),
                    timeout=self._timeouts[purpose],
                )
                return result.generations[0].message.content
            except asyncio.TimeoutError:
                logger.warning(f"LLM {purpose} timed out (attempt {attempt+1})")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"LLM {purpose} failed (attempt {attempt+1}): {e}")
            if attempt < self._retries[purpose]:
                await asyncio.sleep(0.5)
        logger.error(f"LLM {purpose} degraded")
        return None

    async def call_structured(
        self, purpose: str, schema: type[BaseModel],
        messages: list[BaseMessage], fallback: Callable[[], BaseModel],
    ) -> BaseModel:
        model = self._models[purpose]
        for attempt in range(self._retries[purpose] + 1):
            try:
                result = await asyncio.wait_for(
                    model._agenerate(messages, response_format={"type": "json_object"}),
                    timeout=self._timeouts[purpose],
                )
                content = result.generations[0].message.content
                return schema.model_validate_json(content)
            except asyncio.TimeoutError:
                logger.warning(f"LLM {purpose} structured timed out (attempt {attempt+1})")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"LLM {purpose} structured failed (attempt {attempt+1}): {e}")
            if attempt < self._retries[purpose]:
                await asyncio.sleep(0.5)
        logger.error(f"LLM {purpose} structured degraded")
        return fallback()
