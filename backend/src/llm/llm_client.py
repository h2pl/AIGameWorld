"""LLM 客户端——多模型路由，支持 langchain(ChatOpenAI) 和 requests(RequestsChatModel) 双后端."""

import asyncio
import os
import re
import time
from collections.abc import Callable
from typing import Any

import requests
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from ..config import Config, LLMModelConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)

# ============================================================
# 企业级日志辅助
# ============================================================


def _log_ctx(purpose: str, attempt: int, max_attempts: int, **kwargs: Any) -> dict[str, Any]:
    """构建结构化日志上下文."""
    ctx: dict[str, Any] = {
        "purpose": purpose,
        "attempt": f"{attempt + 1}/{max_attempts}",
        **kwargs,
    }
    return ctx


def _model_name(model: BaseChatModel) -> str:
    """提取模型可读名称，避免在日志中打印对象 repr（含内存地址、密钥）."""
    for attr in ("model_name", "model"):
        if hasattr(model, attr):
            value = getattr(model, attr)
            if value:
                return str(value)
    return type(model).__name__


# ============================================================
# RequestsChatModel —— 解决 Zen Proxy 502
# ============================================================


class RequestsChatModel(BaseChatModel):
    """用 requests 替代 httpx 的 ChatModel——解决 Zen Proxy 502 问题."""

    model: str = ""
    temperature: float = 0.7
    base_url: str = ""
    timeout: int = 30

    def _generate(self, tick_messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        raise NotImplementedError("Use async version")

    async def _agenerate(
        self, tick_messages: list[BaseMessage], stop=None, run_manager=None, **kwargs
    ):
        _role_map = {"human": "user", "ai": "assistant"}
        msg_count = len(tick_messages)
        payload = {
            "model": self.model,
            "tick_messages": [
                {"role": _role_map.get(m.type, m.type), "content": m.content} for m in tick_messages
            ],
            "temperature": self.temperature,
        }
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        url = f"{self.base_url}/chat/completions"
        t_start = time.monotonic()
        logger.debug(
            "LLM 请求发送",
            extra={
                "model": self.model,
                "url": url,
                "tick_messages": msg_count,
                "timeout": self.timeout,
            },
        )

        loop = asyncio.get_event_loop()
        try:
            resp = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, timeout=self.timeout),
            )
            elapsed = time.monotonic() - t_start
            logger.debug(
                "LLM 收到响应",
                extra={
                    "model": self.model,
                    "status": resp.status_code,
                    "elapsed": f"{elapsed:.1f}s",
                },
            )
            resp.raise_for_status()
        except requests.Timeout as e:
            elapsed = time.monotonic() - t_start
            logger.error(
                "LLM HTTP 超时——服务端在超时窗口内未返回任何数据",
                extra={
                    "model": self.model,
                    "url": url,
                    "http_timeout": f"{self.timeout}s",
                    "elapsed": f"{elapsed:.1f}s",
                },
            )
            raise RuntimeError(
                f"HTTP 请求超时：{url} 在 {self.timeout}s 内无响应（已等待 {elapsed:.1f}s）"
            ) from e
        except requests.ConnectionError as e:
            logger.error(
                "LLM 连接失败——代理或服务端不可达",
                extra={"model": self.model, "url": url, "error": str(e)},
            )
            raise RuntimeError(f"连接失败：{url} — {e}") from e
        except requests.HTTPError as e:
            body = e.response.text[:500] if e.response is not None else "(无响应体)"
            logger.error(
                "LLM HTTP 错误",
                extra={
                    "model": self.model,
                    "url": url,
                    "status": e.response.status_code if e.response else "?",
                    "body": body,
                },
            )
            raise RuntimeError(f"HTTP {e.response.status_code}：{body}") from e

        data = resp.json()
        finish_reason = data["choices"][0].get("finish_reason", "?")
        content: str = data["choices"][0]["message"]["content"]
        logger.debug(
            "LLM 响应内容",
            extra={
                "model": self.model,
                "finish_reason": finish_reason,
                "content_len": len(content),
                "content_preview": content[:120],
            },
        )
        # 提取 token 用量 / Extract token usage from API response
        llm_output: dict[str, Any] = {}
        usage_metadata: dict[str, int] | None = None
        if "usage" in data:
            u = data["usage"]
            tokens_in = u.get("prompt_tokens", 0)
            tokens_out = u.get("completion_tokens", 0)
            llm_output["token_usage"] = {
                "prompt_tokens": tokens_in,
                "completion_tokens": tokens_out,
                "total_tokens": u.get("total_tokens", 0),
            }
            # ainvoke() 返回 AIMessage，token 信息通过 usage_metadata 传递
            usage_metadata = {
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "total_tokens": u.get("total_tokens", 0),
            }
        msg = AIMessage(content=content)
        if usage_metadata:
            msg.usage_metadata = usage_metadata  # type: ignore[assignment]
        return ChatResult(
            generations=[ChatGeneration(message=msg)],
            llm_output=llm_output,
        )

    @property
    def _llm_type(self) -> str:
        return "requests-chat"


# ============================================================
# Proxy JSON 提示 / Proxy JSON hint
# ============================================================


def _prep_proxy(tick_messages: list[BaseMessage], schema: type[BaseModel]) -> list[BaseMessage]:
    """Proxy 模式：末尾追加 JSON 格式提示 / Append JSON format hint for proxy backends."""
    fields = schema.model_fields
    field_desc = ", ".join(
        f"{k}({v.annotation.__name__ if hasattr(v.annotation, '__name__') else str(v.annotation)})"
        for k, v in fields.items()
    )
    json_hint = HumanMessage(content=f"请只输出一个 JSON 对象，字段：{{{field_desc}}}")
    return list(tick_messages) + [json_hint]


# ============================================================
# JSON 提取 / JSON extraction
# ============================================================


def _extract_json(text: str) -> str:
    """从 LLM 回复中提取 JSON——兼容 markdown code block 包裹."""
    # 尝试匹配 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return m.group(1).strip()
    # 尝试匹配第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


# ============================================================
# Langchain Model 构建
# ============================================================


def _build_model_langchain(
    cfg: LLMModelConfig, base_url: str | None, api_key: str | None = None
) -> BaseChatModel:
    """使用 LangChain ChatOpenAI（标准 OpenAI 兼容 API）."""
    return ChatOpenAI(
        model=cfg.model,
        temperature=cfg.temperature,
        base_url=(base_url or "https://api.openai.com/v1"),
        api_key=api_key or "sk-dummy",
        timeout=cfg.timeout,
        max_retries=cfg.retries,
    )


def _build_model_requests(
    cfg: LLMModelConfig, base_url: str | None, api_key: str | None = None
) -> BaseChatModel:
    """使用 requests 直连（Zen Proxy / Node.js 代理兼容）."""
    return RequestsChatModel(
        model=cfg.model,
        temperature=cfg.temperature,
        base_url=(base_url or "https://api.openai.com/v1").rstrip("/"),
    )


def _build_model(
    cfg: LLMModelConfig, base_url: str | None, api_key: str | None = None
) -> BaseChatModel:
    """根据 client_backend 选择后端构建 ChatModel."""
    backend = cfg.client_backend or "langchain"
    if backend == "requests":
        return _build_model_requests(cfg, base_url, api_key)
    return _build_model_langchain(cfg, base_url, api_key)


def _build_fallback_model(
    cfg: LLMModelConfig, fallback_base_url: str | None, api_key: str | None = None
) -> BaseChatModel | None:
    """构建降级模型（与主模型使用相同 backend）."""
    if not cfg.fallback_model:
        return None
    backend = cfg.client_backend or "langchain"
    if backend == "requests":
        return RequestsChatModel(
            model=cfg.fallback_model,
            temperature=cfg.temperature,
            base_url=(fallback_base_url or "https://api.openai.com/v1").rstrip("/"),
        )
    return ChatOpenAI(
        model=cfg.fallback_model,
        temperature=cfg.temperature,
        base_url=(fallback_base_url or "https://api.openai.com/v1"),
        api_key=api_key or "sk-dummy",
        timeout=cfg.timeout,
        max_retries=cfg.retries,
    )


def _inject_anthropic_cache(messages: list[BaseMessage]) -> list[BaseMessage]:
    """为 Anthropic 家族模型注入 Prompt Caching 的 ephemeral 标记.
    
    Anthropic 要求将 cache_control 放在 block 内部。
    我们会将消息列表中最后一个 SystemMessage 标记为可缓存的端点。
    由于世界观、GraphRAG 等都在 SystemMessage 中，这能最大化缓存命中率。
    """
    if not messages:
        return messages
        
    augmented = list(messages)
    # 找到最后一个 SystemMessage
    last_sys_idx = -1
    for i, msg in enumerate(augmented):
        if isinstance(msg, SystemMessage):
            last_sys_idx = i
            
    if last_sys_idx >= 0:
        msg = augmented[last_sys_idx]
        if isinstance(msg.content, str):
            # 转换为 Anthropic 支持的 content blocks 格式
            augmented[last_sys_idx] = SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": msg.content,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            )
    return augmented

# ============================================================
# LLMClient —— 重试 + 结构化调用
# ============================================================


class LLMClient:
    """多模型 LLM 客户端——统一 mock 开关 + 数据集切换."""

    def __init__(self, config: Config):
        self._mock = config.llm_mock
        self._mock_dataset = config.mock_dataset
        llm_config = config.llm
        key_env = llm_config.providers.primary.api_key_env
        primary_key = os.environ.get(key_env, "") if key_env else ""
        primary_url = llm_config.providers.primary.base_url
        fallback_url = (
            llm_config.providers.fallback.base_url if llm_config.providers.fallback else None
        )

        self._models: dict[str, BaseChatModel] = {}
        self._fallbacks: dict[str, BaseChatModel | None] = {}
        self._timeouts: dict[str, int] = {}
        self._retries: dict[str, int] = {}
        self._metrics_collector: Any = None  # 由 server.py 注入 / Injected by server.py
        self._current_world_id = ""  # 由 orchestrator 每个 tick 设置 / Set per-tick by orchestrator

        for purpose, cfg in [
            ("dm_create", llm_config.dm_create),
            ("dm_narrate", llm_config.dm_narrate),
            ("pc_decision", llm_config.pc_decision),
            ("actor_decision", llm_config.actor_decision),
            ("talk", llm_config.talk),
            ("interact", llm_config.interact),
            ("explore", llm_config.explore),
            ("combat", llm_config.combat),
            ("reflection", llm_config.reflection),
        ]:
            model_url = cfg.base_url or primary_url
            self._models[purpose] = _build_model(cfg, model_url, primary_key)
            self._fallbacks[purpose] = _build_fallback_model(cfg, fallback_url)
            self._timeouts[purpose] = cfg.timeout
            self._retries[purpose] = cfg.retries

    # --------------------------------------------------------
    # 指标收集 / Metrics recording
    # --------------------------------------------------------

    def set_context(self, world_id: str) -> None:
        """设置当前 tick 的 world_id，供指标收集使用 / Set current world_id for metrics."""
        self._current_world_id = world_id

    def _record_tokens_from_message(self, msg: AIMessage) -> None:
        """从 AIMessage.usage_metadata 提取 token 用量并上报 / Record token usage from AIMessage."""
        if not self._metrics_collector or not self._current_world_id:
            return
        usage = getattr(msg, "usage_metadata", None)
        if not usage:
            return
        tokens_in = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)
        if tokens_in or tokens_out:
            self._metrics_collector.record_llm(self._current_world_id, tokens_in, tokens_out)

    # --------------------------------------------------------
    # call —— 纯文本调用
    # --------------------------------------------------------

    async def call(self, purpose: str, tick_messages: list[BaseMessage]) -> str | None:
        if self._mock:
            from .mock_data import get_mock

            data = get_mock(purpose, self._mock_dataset)
            return data.get("narrative", data.get("summary", str(data)))

        model = self._models[purpose]
        timeout = self._timeouts[purpose]
        max_attempts = self._retries[purpose] + 1
        
        # 针对 Anthropic 模型的 Prompt Caching 优化
        augmented = tick_messages
        model_name = _model_name(model).lower()
        if "claude" in model_name or "anthropic" in model_name:
            augmented = _inject_anthropic_cache(tick_messages)

        logger.info(
            f"[{purpose}] 开始调用",
            extra=_log_ctx(
                purpose,
                -1,
                max_attempts,
                model_name=_model_name(model),
                timeout=timeout,
                mode="text",
            ),
        )

        for attempt in range(max_attempts):
            t_start = time.monotonic()
            try:
                # 用 ainvoke()（Runnable API）代替 agenerate()，callbacks 自动从
                # contextvars 传播（LangGraph 已设置），避免 handler 重复注册。
                # / Use ainvoke() (Runnable API) so callbacks propagate from contextvars
                # automatically—no double registration, LLM span attaches to parent trace.
                msg = await asyncio.wait_for(
                    model.ainvoke(augmented),
                    timeout=timeout,
                )
                elapsed = time.monotonic() - t_start
                content = str(msg.content) if msg else ""
                self._record_tokens_from_message(msg)
                logger.info(
                    f"[{purpose}] 调用成功",
                    extra=_log_ctx(
                        purpose,
                        attempt,
                        max_attempts,
                        elapsed=f"{elapsed:.1f}s",
                        content_len=len(content),
                    ),
                )
                return content

            except TimeoutError:
                elapsed = time.monotonic() - t_start
                logger.warning(
                    f"[{purpose}] 应用层超时——等待 {timeout}s 后取消（实际已等 {elapsed:.1f}s），LLM 未在时限内返回完整响应",
                    extra=_log_ctx(
                        purpose,
                        attempt,
                        max_attempts,
                        timeout=f"{timeout}s",
                        elapsed=f"{elapsed:.1f}s",
                        hint="如需更长等待时间，请增加 config.yaml 中该 purpose 的 timeout 值",
                    ),
                )

            except asyncio.CancelledError:
                raise

            except RuntimeError as e:
                logger.error(
                    f"[{purpose}] 网络/协议层错误: {e}",
                    extra=_log_ctx(purpose, attempt, max_attempts, error_type="RuntimeError"),
                    exc_info=True,
                )

            except Exception as e:
                logger.error(
                    f"[{purpose}] 未预期的异常: {type(e).__name__}: {e}",
                    extra=_log_ctx(purpose, attempt, max_attempts, error_type=type(e).__name__),
                    exc_info=True,
                )

            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)

        logger.error(
            f"[{purpose}] 全部 {max_attempts} 次尝试均失败，返回 None",
            extra=_log_ctx(purpose, max_attempts - 1, max_attempts, result="degraded"),
        )
        return None

    # --------------------------------------------------------
    # call_structured —— 结构化 JSON 调用
    # --------------------------------------------------------

    async def call_structured(
        self,
        purpose: str,
        schema: type[BaseModel],
        tick_messages: list[BaseMessage],
        fallback: Callable[[], BaseModel] | None = None,
    ) -> BaseModel:
        """结构化调用——标准用 response_format，Proxy 用 JSON 提示."""
        if self._mock:
            from .mock_data import get_mock

            data = get_mock(purpose, self._mock_dataset)
            try:
                return schema(**data)
            except Exception:
                if fallback:
                    return fallback()
                raise

        model = self._models[purpose]
        timeout = self._timeouts[purpose]
        max_attempts = self._retries[purpose] + 1

        # 标准 API 用 response_format，Proxy 用末尾 JSON 提示 / Standard uses response_format, Proxy appends JSON hint
        if isinstance(model, RequestsChatModel):
            augmented, generate_kwargs = _prep_proxy(tick_messages, schema), {}
        else:
            augmented = tick_messages
            generate_kwargs = {"response_format": {"type": "json_object"}}

        # 针对 Anthropic 模型的 Prompt Caching 优化
        model_name = _model_name(model).lower()
        if "claude" in model_name or "anthropic" in model_name:
            augmented = _inject_anthropic_cache(augmented)

        logger.info(
            f"[{purpose}] 开始结构化调用",
            extra=_log_ctx(
                purpose,
                -1,
                max_attempts,
                model_name=_model_name(model),
                timeout=timeout,
                schema=schema.__name__,
                mode="structured",
            ),
        )

        last_content: str | None = None

        for attempt in range(max_attempts):
            t_start = time.monotonic()
            try:
                # 用 ainvoke()（Runnable API）代替 agenerate()，callbacks 自动从
                # contextvars 传播，避免 handler 重复注册。
                # / Use ainvoke() so callbacks propagate from contextvars automatically.
                msg = await asyncio.wait_for(
                    model.ainvoke(augmented, **generate_kwargs),
                    timeout=timeout,
                )
                elapsed = time.monotonic() - t_start
                content = str(msg.content) if msg else ""
                last_content = content
                self._record_tokens_from_message(msg)

                # 尝试解析 JSON
                json_str = _extract_json(content)
                parsed = schema.model_validate_json(json_str)
                logger.info(
                    f"[{purpose}] 结构化调用成功",
                    extra=_log_ctx(
                        purpose,
                        attempt,
                        max_attempts,
                        elapsed=f"{elapsed:.1f}s",
                        raw_len=len(content),
                        json_len=len(json_str),
                        raw_preview=content[:400],
                        parsed_preview=str(parsed.model_dump())[:400],
                    ),
                )
                return parsed

            except (ValueError, ValidationError) as e:
                # JSON 解析失败——打印原始响应，帮助调试 prompt
                elapsed = time.monotonic() - t_start
                raw = last_content or "(无)"
                logger.error(
                    f"[{purpose}] JSON 解析失败——LLM 返回了非 JSON 内容\n"
                    f"  → 解析错误: {e}\n"
                    f"  → 原始响应（前 500 字符）: {raw[:500]}\n"
                    f"  → 提取的 JSON 片段: {_extract_json(raw)[:200] if raw else '(空)'}",
                    extra=_log_ctx(
                        purpose,
                        attempt,
                        max_attempts,
                        error_type="ValidationError",
                        elapsed=f"{elapsed:.1f}s",
                        raw_preview=raw[:200],
                        json_extract=_extract_json(raw)[:200] if raw else "",
                    ),
                )

            except TimeoutError:
                elapsed = time.monotonic() - t_start
                logger.warning(
                    f"[{purpose}] 应用层超时——等待 {timeout}s 后取消（实际已等 {elapsed:.1f}s），免费模型生成结构化 JSON 较慢\n"
                    f"  → 建议：增加 config.yaml 中 {purpose}.timeout 或换用付费模型",
                    extra=_log_ctx(
                        purpose,
                        attempt,
                        max_attempts,
                        timeout=f"{timeout}s",
                        elapsed=f"{elapsed:.1f}s",
                        hint="免费模型生成 JSON 通常需要更长时间",
                    ),
                )

            except asyncio.CancelledError:
                raise

            except RuntimeError as e:
                logger.error(
                    f"[{purpose}] 网络/协议层错误: {e}",
                    extra=_log_ctx(purpose, attempt, max_attempts, error_type="RuntimeError"),
                    exc_info=True,
                )

            except Exception as e:
                logger.error(
                    f"[{purpose}] 未预期的异常: {type(e).__name__}: {e}",
                    extra=_log_ctx(purpose, attempt, max_attempts, error_type=type(e).__name__),
                    exc_info=True,
                )

            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)

        logger.error(
            f"[{purpose}] 全部 {max_attempts} 次结构化调用均失败，启用 fallback",
            extra=_log_ctx(purpose, max_attempts - 1, max_attempts, result="degraded"),
        )
        if fallback:
            return fallback()
        raise RuntimeError(
            f"[{purpose}] all {max_attempts} attempts failed and no fallback configured"
        )


# Mock 数据已统一迁移至 mock_data.py / Mock data centralized in mock_data.py
