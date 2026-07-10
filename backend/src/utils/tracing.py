"""链路追踪 / Distributed Tracing.

双追踪架构：
- LangSmith：开发期调试 + Prompt 实验 + 评估回归（与 LangGraph 原生集成，环境变量驱动）
- Langfuse：生产期监控 + Token 成本 + 延迟告警（CallbackHandler + 全链路 span）

Langfuse 全链路 trace 架构（官方推荐 + 全链路 span）：
1. orchestrator.run_tick 用 start_as_current_observation 创建 root span
2. propagate_attributes 设置 session_id/user_id/trace_name/tags
3. CallbackHandler 自动追踪 LangGraph 节点 + LLM 调用
4. @traced 装饰器在 engine/repo 层创建子 span（挂到 root span 下）
5. trace_db 在 storage 层创建 DB 操作 span

@traced 和 trace_db 会检查当前 OTel context 是否有有效父 span，
无父 span 时跳过 span 创建，避免孤儿 trace。
/ @traced and trace_db check for valid parent span in OTel context,
skip span creation when no parent exists to avoid orphan traces.

参考文档：
- https://langfuse.com/integrations/frameworks/langchain
- https://langfuse.com/docs/observability/features/sessions
"""

import functools
import os
from typing import Any, Callable, TypeVar

from opentelemetry import trace as otel_trace

from src.utils.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def is_langfuse_enabled() -> bool:
    """检查 Langfuse 是否启用 / Check if Langfuse tracing is enabled."""
    return os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"


def _has_parent_span() -> bool:
    """检查当前 OTel context 是否有有效父 span / Check for valid parent span.

    无父 span 时返回 False，用于避免创建孤儿 trace。
    / Returns False when no parent span exists, preventing orphan traces.
    """
    current_span = otel_trace.get_current_span()
    return current_span.get_span_context().is_valid


def traced(name: str | None = None) -> Callable[[F], F]:
    """异步方法装饰器：在 Langfuse 中创建子 span / Decorator: create child span in Langfuse.

    span name 自动从 __module__ 和函数名推断（如 "dm.DmEngine.dm_create"），
    或通过 name 参数显式指定。

    无父 span 时跳过 span 创建，避免孤儿 trace。
    / Skips span creation when no parent span exists to avoid orphan traces.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not is_langfuse_enabled() or not _has_parent_span():
                return await func(*args, **kwargs)

            span_name = name or f"{func.__module__}.{func.__qualname__}"
            # 去掉 src. 前缀 / Strip src. prefix
            if span_name.startswith("src."):
                span_name = span_name[4:]

            try:
                from langfuse import get_client

                langfuse = get_client()
                with langfuse.start_as_current_observation(as_type="span", name=span_name) as span:
                    if span:
                        span._otel_span.set_attribute("method", func.__qualname__)
                    return await func(*args, **kwargs)
            except Exception:
                # Langfuse 不可用时直接执行 / Execute directly when Langfuse unavailable
                return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def create_langfuse_handler(tick: int, world_id: str) -> Any | None:
    """创建 Langfuse 回调处理器 / Create Langfuse callback handler.

    Langfuse v4 SDK：
    - 导入路径 langfuse.langchain（非 v2/v3 的 langfuse.callback）
    - CallbackHandler() 无参，依赖环境变量初始化全局 client
    - 环境变量名 LANGFUSE_HOST（非 v3 的 LANGFUSE_BASE_URL）
    - trace 元数据通过 LangChain config["metadata"] 的 langfuse_* 前缀字段传递
    """
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse.langchain import CallbackHandler

        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")

        if not public_key or not secret_key:
            logger.warning("[tracing] LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set, skipping")
            return None

        # v4：CallbackHandler 无参，依赖全局 client（由环境变量初始化）/ v4: handler is parameterless
        handler = CallbackHandler()

        logger.info(
            "[tracing] Langfuse v4 handler created for tick=%s world=%s",
            tick,
            world_id,
        )
        return handler
    except ImportError:
        logger.warning("[tracing] langfuse not installed or v4+ required, skipping")
        return None
    except Exception as e:
        logger.warning("[tracing] failed to create Langfuse handler: %s", e)
        return None


def get_langfuse_metadata(tick: int, world_id: str) -> dict[str, Any]:
    """获取 Langfuse v4 trace 元数据 / Get Langfuse v4 trace metadata.

    Langfuse v4 CallbackHandler 会从 LangChain config["metadata"] 中读取
    `langfuse_*` 前缀字段，自动应用到它创建的 trace 上：
    - langfuse_trace_name：trace 名称，显示在 Langfuse 面板列表中
    - langfuse_session_id：同一 world 的所有 tick 聚合到同一 session
    - langfuse_user_id：用户标识（这里用 world_id）
    - langfuse_tags：trace 标签，便于跨维度筛选
    """
    if not is_langfuse_enabled():
        return {}
    trace_name = f"{world_id}__tick_{tick}"
    return {
        "langfuse_trace_name": trace_name,  # trace 名称 / Trace name in panel
        "langfuse_session_id": world_id,  # 同一 world 聚合 / Aggregate by world
        "langfuse_user_id": world_id,
        "langfuse_tags": [f"world:{world_id}", f"tick:{tick}"],
        "world_id": world_id,
        "tick": tick,
    }


# ── LangSmith：开发期调试与评估 / LangSmith: Dev-time debugging & evaluation ──


def is_langsmith_enabled() -> bool:
    """检查 LangSmith 是否启用 / Check if LangSmith tracing is enabled.

    LangSmith 通过环境变量与 LangGraph 深度集成：
    - LANGCHAIN_TRACING_V2=true 启用追踪
    - LANGCHAIN_API_KEY 设置 API 密钥
    - LANGCHAIN_PROJECT 设置项目名

    无需额外代码，LangGraph 自动将节点/LLM调用上报 LangSmith。
    """
    return os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true"


def configure_langsmith() -> None:
    """配置 LangSmith 环境 / Configure LangSmith environment.

    在应用启动时调用，确保环境变量正确设置。
    LangSmith 原生集成 LangGraph，不需要手动创建 handler。
    """
    if not is_langsmith_enabled():
        return

    # 确保 API Key 已设置 / Ensure API key is set
    api_key = os.environ.get("LANGCHAIN_API_KEY", "")
    if not api_key:
        logger.warning("[tracing] LANGCHAIN_API_KEY not set, LangSmith tracing will not work")
        return

    project = os.environ.get("LANGCHAIN_PROJECT", "aigameworld")
    endpoint = os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    logger.info(
        "[tracing] LangSmith enabled: project=%s endpoint=%s",
        project,
        endpoint,
    )
