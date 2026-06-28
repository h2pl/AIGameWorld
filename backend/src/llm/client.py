"""LLM 客户端——OpenAI-compatible + 重试 + 降级链."""

import asyncio
import logging
from typing import Any, Type

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

from ..config import LLMModelConfig, ProviderConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI-compatible LLM 客户端，支持重试和降级链.

    Usage:
        client = LLMClient(provider=primary_provider, model_cfg=dm_create_cfg)
        response = await client.chat(messages=messages)
        structured = await client.structured(messages, DMCreateResponse)
    """

    def __init__(self, provider: ProviderConfig, model_cfg: LLMModelConfig):
        self._provider = provider
        self._cfg = model_cfg
        self._fallback: AsyncOpenAI | None = None
        self._client = AsyncOpenAI(
            base_url=provider.base_url or "https://api.openai.com/v1",
            api_key="sk-placeholder",  # 从环境变量读取 / Read from env
        )

    @property
    def model(self) -> str:
        return self._cfg.model

    async def chat(self, messages: list[dict], **kwargs) -> ChatCompletion:
        """普通聊天补全 / Plain chat completion."""
        return await self._invoke(messages, **kwargs)

    async def structured(
        self,
        messages: list[dict[str, str]],
        response_format: Type[BaseModel],
        **kwargs,
    ) -> BaseModel:
        """结构化输出 / Structured output via Pydantic model."""
        completion = await self._invoke(
            messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_format.__name__,
                    "schema": response_format.model_json_schema(),
                },
            },
            **kwargs,
        )
        content = completion.choices[0].message.content or "{}"
        return response_format.model_validate_json(content)

    async def _invoke(self, messages: list[dict], **kwargs) -> ChatCompletion:
        """带重试和降级的实际调用 / Invoke with retry + fallback."""
        last_error: Exception | None = None

        for attempt in range(self._cfg.retries + 1):
            try:
                return await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self._cfg.model,
                        messages=messages,
                        temperature=self._cfg.temperature,
                        **kwargs,
                    ),
                    timeout=self._cfg.timeout,
                )
            except Exception as e:
                last_error = e
                if attempt < self._cfg.retries:
                    wait = 2**attempt
                    logger.warning(
                        f"LLM retry {attempt + 1}/{self._cfg.retries} "
                        f"after {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)

        # 降级到 fallback_model / Fallback to fallback model
        if self._cfg.fallback_model:
            logger.warning(f"Fallback to model: {self._cfg.fallback_model}")
            try:
                kwargs.pop("response_format", None)  # fallback 可能不支持 structured
                return await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self._cfg.fallback_model,
                        messages=messages,
                        temperature=self._cfg.temperature,
                    ),
                    timeout=self._cfg.timeout,
                )
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")

        raise RuntimeError(
            f"LLM call failed after {self._cfg.retries} retries: {last_error}"
        )
