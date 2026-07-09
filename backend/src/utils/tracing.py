"""链路追踪 / Distributed Tracing.

双追踪架构：
- LangSmith：开发期调试 + Prompt 实验 + 评估回归（与 LangGraph 原生集成）
- Langfuse：生产期监控 + Token 成本 + 延迟告警（OTel-native 自托管）

LangSmith 通过环境变量自动集成（LANGCHAIN_TRACING_V2=true），
Langfuse 通过 CallbackHandler 注入 config["callbacks"]。
"""

import os
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


def is_langfuse_enabled() -> bool:
    """检查 Langfuse 是否启用 / Check if Langfuse tracing is enabled."""
    return os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"


def create_langfuse_handler(tick: int, world_id: str) -> Any | None:
    """创建 Langfuse 回调处理器 / Create Langfuse callback handler.

    如果 Langfuse 未启用（LANGFUSE_ENABLED != true），返回 None。
    返回的 handler 可直接注入 LangGraph config["callbacks"]。
    """
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse.callback import CallbackHandler

        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
        base_url = os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3000")

        if not public_key or not secret_key:
            logger.warning("[tracing] LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set, skipping")
            return None

        handler = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=base_url,
            trace_name=f"tick-{tick}",
            tags=[f"world:{world_id}", f"tick:{tick}"],
            metadata={"world_id": world_id, "tick": tick},
        )
        logger.info("[tracing] Langfuse handler created for tick=%s world=%s", tick, world_id)
        return handler
    except ImportError:
        logger.warning("[tracing] langfuse not installed, skipping")
        return None
    except Exception as e:
        logger.warning("[tracing] failed to create Langfuse handler: %s", e)
        return None


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
