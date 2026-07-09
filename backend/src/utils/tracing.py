"""链路追踪 / Distributed Tracing.

双追踪架构：
- LangSmith：开发期调试 + Prompt 实验 + 评估回归（与 LangGraph 原生集成）
- Langfuse：生产期监控 + Token 成本 + 延迟告警（OTel-native 自托管）

LangSmith 通过环境变量自动集成（LANGCHAIN_TRACING_V2=true），
Langfuse v4 通过 langfuse.langchain.CallbackHandler 注入 config["callbacks"]。
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

    v4 通过 LangChain config["metadata"] 的 langfuse_* 前缀字段设置 trace 属性。
    - session_id 用 world_id，同一 world 的所有 tick 聚合到同一个 session
    - tags 标记 world 和 tick，便于跨维度筛选
    """
    if not is_langfuse_enabled():
        return {}
    return {
        "langfuse_session_id": world_id,  # 同一 world 聚合 / Aggregate by world
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
