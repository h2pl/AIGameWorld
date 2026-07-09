"""链路追踪 / Distributed Tracing.

双追踪架构：
- LangSmith：开发期调试 + Prompt 实验 + 评估回归（与 LangGraph 原生集成）
- Langfuse：生产期监控 + Token 成本 + 延迟告警（OTel-native 自托管）

全链路 trace 串联（各 Python 层级）：
1. FastAPI 中间件用 start_request_span 创建 root span（HTTP 入口）
2. Orchestrator 用 @traced 装饰 run_tick（编排层）
3. CallbackHandler 自动为 LangGraph 节点/LLM 调用创建 observation（graph + service 层）
4. Engine 层用 @traced 装饰各引擎入口方法（dm/decision/combat/explore/interact/talk/reflection）
5. Repository 层用 @traced 装饰各 repo 方法（world/scene/actor/pc/event/dm_record/memory）
6. Storage 层用 trace_db 创建 DB 操作子 span（sqlite_client）

层级示例：
  HTTP GET /api/world/{id}/tick/next        ← start_request_span (root)
  └── orchestrator.run_tick                 ← @traced
      └── LangGraph                         ← CallbackHandler root run
          ├── dm_service.dm_create
          │   ├── engine.dm_engine.dm_create ← @traced
          │   │   └── ChatOpenAI
          │   └── repo.dm_record.insert      ← @traced
          │       └── db.execute             ← trace_db
          ├── pc_service.decide
          │   └── engine.decision_engine.decide ← @traced
          │       └── ChatOpenAI
          ├── data_service.persist_tick
          │   └── repo.event_repo.insert     ← @traced
          │       └── db.execute             ← trace_db
          └── reflection_service.reflect
"""

import functools
import os
import re
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


def is_langfuse_enabled() -> bool:
    """检查 Langfuse 是否启用 / Check if Langfuse tracing is enabled."""
    return os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"


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
        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not public_key or not secret_key:
            logger.warning("[tracing] LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set, skipping")
            return None

        # v4：CallbackHandler 无参，依赖全局 client（由环境变量初始化）/ v4: handler is parameterless
        handler = CallbackHandler()

        logger.info(
            "[tracing] Langfuse v4 handler created for tick=%s world=%s host=%s",
            tick,
            world_id,
            host,
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

    注意：CallbackHandler 在 root run 时会检测当前 OTel span context，
    如果有效则自动挂到当前 trace（由 FastAPI 中间件的 start_request_span 创建）。
    CallbackHandler 内部通过 _attach_observation 设置 OTel context，
    使节点内部的 DB span 自动挂到节点 observation 下。
    / CallbackHandler auto-detects OTel context at root run, attaching to the
    FastAPI middleware's root span. It sets OTel context per node via
    _attach_observation, so DB spans inside nodes nest under the node observation.
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


# ── 全链路 trace：HTTP 入口 + DB 层 / Full-chain trace: HTTP entry + DB layer ──

# 从路径提取 world_id 的正则 / Extract world_id from URL path
_WORLD_ID_PATTERN = re.compile(r"/api/world/([^/]+)")


def _extract_world_id(path: str) -> str | None:
    """从 URL 路径提取 world_id / Extract world_id from URL path."""
    m = _WORLD_ID_PATTERN.search(path)
    return m.group(1) if m else None


@contextmanager
def start_request_span(method: str, path: str) -> Generator[Any | None, None, None]:
    """创建 HTTP 请求 root span / Create HTTP request root span.

    在 FastAPI 中间件中调用，创建 Langfuse root span。
    CallbackHandler 会自动检测此 span 的 OTel context，将 LangGraph trace 挂到其下。
    / Called in FastAPI middleware to create a Langfuse root span.
    CallbackHandler auto-detects this span's OTel context and attaches LangGraph trace.

    Args:
        method: HTTP 方法 / HTTP method (GET, POST, ...)
        path: 请求路径 / Request path

    Yields:
        LangfuseSpan | None: root span，Langfuse 未启用时为 None
    """
    if not is_langfuse_enabled():
        yield None
        return

    try:
        from langfuse import get_client, propagate_attributes
    except ImportError:
        yield None
        return

    world_id = _extract_world_id(path)
    span_name = f"HTTP {method} {path}"
    langfuse = get_client()

    with langfuse.start_as_current_observation(name=span_name, as_type="span") as span:
        # 设置 trace 级属性：session/user/tags 按 world 聚合
        # / Set trace-level attrs: aggregate by world via session/user/tags
        if world_id and span:
            # 直接在 OTel span 上设置 trace 级属性，确保 Langfuse 后端读取到
            # / Set trace-level attrs directly on OTel span for reliable backend ingestion
            otel_span = getattr(span, "_otel_span", None)
            if otel_span and otel_span.is_recording():
                otel_span.set_attribute("session.id", world_id)
                otel_span.set_attribute("user.id", world_id)
            with propagate_attributes(
                session_id=world_id,
                user_id=world_id,
                tags=[f"world:{world_id}"],
            ):
                yield span
        else:
            yield span


@asynccontextmanager
async def trace_db(operation: str, sql: str | None = None):
    """创建 DB 操作子 span / Create DB operation child span.

    在 SQLiteClient 的 execute/fetch_all/fetch_one 中调用。
    用 Langfuse SDK 创建 span（scope=langfuse），确保被 Langfuse 导出。
    自动挂到当前 OTel context（LangGraph 节点 observation 或 HTTP root span）。
    / Called in SQLiteClient methods. Uses Langfuse SDK (scope=langfuse) to ensure
    export. Auto-attaches to current OTel context (node observation or root span).

    Args:
        operation: 操作名 / Operation name (e.g. "execute", "fetch_all")
        sql:       SQL 语句（可选，截断到 200 字符）/ SQL statement (optional, truncated)
    """
    if not is_langfuse_enabled():
        yield None
        return

    try:
        from langfuse import get_client
    except ImportError:
        yield None
        return

    langfuse = get_client()
    with langfuse.start_as_current_observation(name=f"db.{operation}", as_type="span") as span:
        # LangfuseSpan 无公共 set_attribute，需通过 _otel_span 设置 / LangfuseSpan has no
        # public set_attribute; set via the underlying OTel span.
        otel_span = getattr(span, "_otel_span", None) if span else None
        if otel_span and otel_span.is_recording():
            otel_span.set_attribute("db.system", "sqlite")
            if sql:
                otel_span.set_attribute("db.statement", sql[:200])
        yield span


# ── 通用层级 span + 装饰器 / Generic layer span + decorator ──


@asynccontextmanager
async def trace_span(name: str, **attributes: Any):
    """创建通用层级 span / Create a generic layer span.

    用于 orchestrator / engine / repository 层的方法追踪。
    自动挂到当前 OTel context（LangGraph 节点 observation 或 HTTP root span）。
    / Used for orchestrator / engine / repository layer method tracing.
    Auto-attaches to current OTel context (node observation or root span).

    Args:
        name: span 名称 / span name (e.g. "engine.dm_create", "repo.get_world")
        **attributes: 附加属性 / additional attributes set on the span
    """
    if not is_langfuse_enabled():
        yield None
        return

    try:
        from langfuse import get_client
    except ImportError:
        yield None
        return

    langfuse = get_client()
    with langfuse.start_as_current_observation(name=name, as_type="span") as span:
        otel_span = getattr(span, "_otel_span", None) if span else None
        if otel_span and otel_span.is_recording():
            for k, v in attributes.items():
                otel_span.set_attribute(k, str(v) if not isinstance(v, (int, float, bool)) else v)
        yield span


def traced(name: str | None = None) -> Callable:
    """异步方法追踪装饰器 / Async method tracing decorator.

    用法 / Usage:
        @traced()                  # span 名自动取 "layer.ClassName.method"
        @traced("engine.dm_create")  # 指定 span 名

    自动从 __module__ 推断层级前缀（engine / repository / orchestrator）。
    / Auto-infers layer prefix from __module__.
    """

    def decorator(func: Callable) -> Callable:
        if name:
            span_name = name
        else:
            module_parts = func.__module__.split(".")
            layer = module_parts[-2] if len(module_parts) >= 2 else module_parts[-1]
            span_name = f"{layer}.{func.__qualname__}"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async with trace_span(span_name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


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
