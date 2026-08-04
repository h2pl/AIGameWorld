"""LangGraph Checkpoint Saver 统一工厂。

Saver 选型:
  | Saver          | 存储位置   | 持久化 | 适用场景               |
  |----------------|-----------|--------|-----------------------|
  | MemorySaver    | 内存      | 否     | 开发、单元测试          |
  | SqliteSaver    | SQLite    | 是     | 单机 MVP、本地运行      |
  | PostgresSaver  | PostgreSQL| 是     | 生产多实例、共享状态    |
  | RedisSaver     | Redis     | 是     | 高性能、短状态共享      |

Checkpoint 是图执行快照，不是业务存档（业务数据由 WorldStateStore 持久化）。
"""

from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from ..utils.logging import get_logger

logger = get_logger(__name__)


def create_checkpointer(
    saver_type: Literal["memory", "sqlite", "postgres", "redis"] = "memory",
    **kwargs,
) -> BaseCheckpointSaver:
    """创建 Checkpointer 工厂 / Create checkpointer by type.

    所有 Saver 均延迟导入，避免开发环境引入不必要的依赖。
    All savers are lazily imported to avoid unnecessary dev dependencies.

    Args:
        saver_type: 存储后端类型 / backend type
        **kwargs: 传给具体 Saver 的构造参数 / constructor args for the chosen saver

    Returns:
        BaseCheckpointSaver: LangGraph checkpointer 实例

    Raises:
        ValueError: 不支持的 saver_type / unsupported saver_type
    """
    logger.info("[graph] checkpointer type=%s", saver_type)
    if saver_type == "memory":
        return MemorySaver()

    if saver_type == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver  # 依赖 aiosqlite

        conn_string = kwargs.get("conn_string", ":memory:")
        return SqliteSaver.from_conn_string(conn_string)

    if saver_type == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver  # 依赖 psycopg

        return PostgresSaver.from_conn_string(kwargs["conn_string"])

    if saver_type == "redis":
        from langgraph.checkpoint.redis import RedisSaver  # 依赖 redis

        return RedisSaver.from_url(kwargs["redis_url"])

    raise ValueError(f"Unsupported saver_type: {saver_type}")


def create_dev_checkpointer() -> BaseCheckpointSaver:
    """开发用内存 Checkpointer（重启丢失）。"""
    return create_checkpointer("memory")


def create_sqlite_checkpointer(conn_string: str) -> BaseCheckpointSaver:
    """SQLite 持久化 Checkpointer。conn_string 如 sqlite:///data/checkpoints.db"""
    return create_checkpointer("sqlite", conn_string=conn_string)


def create_postgres_checkpointer(conn_string: str) -> BaseCheckpointSaver:
    """PostgreSQL 持久化 Checkpointer。"""
    return create_checkpointer("postgres", conn_string=conn_string)


def create_redis_checkpointer(redis_url: str) -> BaseCheckpointSaver:
    """Redis 持久化 Checkpointer。"""
    return create_checkpointer("redis", redis_url=redis_url)
