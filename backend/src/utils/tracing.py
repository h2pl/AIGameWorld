"""链路追踪 / Distributed Tracing.

基于 Langfuse SDK 实现 OpenTelemetry 兼容的链路追踪。
Langfuse 作为 OTel-native 平台，自动从 LangGraph callbacks 中提取：
- Graph 节点 Span（dm_create / pc_decision / dm_narrate 等）
- LLM 调用 Generation（model / tokens / latency）
- 按 tick / world_id 组织 Trace
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
