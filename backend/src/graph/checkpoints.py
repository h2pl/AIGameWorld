"""Checkpoint 配置 / Checkpoint configuration.

基于 design/03-orchestration-layer.md §4 / Based on orchestration layer design.

本文件是 LangGraph Checkpoint Saver 的统一工厂。
All LangGraph checkpoint savers are created through this factory.

Checkpoint 是什么 / What is checkpoint:
  LangGraph 在图执行过程中自动保存的"执行快照"，用于：
  - tick 内部崩溃后恢复 / resume after crash inside a tick
  - 时间旅行调试 / time-travel debugging
  - 回滚到任意节点重跑 / rerun from any node

它不是业务存档 / Not business save:
  Checkpoint 存的是"图执行状态"，不是"游戏世界状态"。
  角色 HP、位置、物品等业务数据由 storage.WorldStateStore 持久化。

Saver 选型 / Saver selection:
  | Saver          | 存储位置   | 持久化 | 适用场景                 |
  |----------------|-----------|--------|-------------------------|
  | MemorySaver    | 内存      | 否     | 开发、单元测试           |
  | SqliteSaver    | SQLite    | 是     | 单机 MVP、本地运行       |
  | PostgresSaver  | PostgreSQL| 是     | 生产多实例、共享状态     |
  | RedisSaver     | Redis     | 是     | 高性能、短状态共享       |
"""

from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver


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
    if saver_type == "memory":
        # 内存存储：速度快，无持久化，重启丢失 / Fast, non-persistent, lost on restart
        return MemorySaver()

    if saver_type == "sqlite":
        # SQLite 文件存储：单机持久化 / File-based persistence for single-node deployment
        # 需要依赖 aiosqlite / requires aiosqlite
        from langgraph.checkpoint.sqlite import SqliteSaver

        conn_string = kwargs.get("conn_string", ":memory:")
        return SqliteSaver.from_conn_string(conn_string)

    if saver_type == "postgres":
        # PostgreSQL 存储：生产多实例共享 / Production shared persistence
        # 需要依赖 psycopg / requires psycopg
        from langgraph.checkpoint.postgres import PostgresSaver

        conn_string = kwargs["conn_string"]  # 必填 / required
        return PostgresSaver.from_conn_string(conn_string)

    if saver_type == "redis":
        # Redis 存储：高性能、短状态共享 / High-performance short-state sharing
        # 需要依赖 redis / requires redis
        from langgraph.checkpoint.redis import RedisSaver

        redis_url = kwargs["redis_url"]  # 必填 / required
        return RedisSaver.from_url(redis_url)

    raise ValueError(f"Unsupported saver_type: {saver_type}")


def create_dev_checkpointer() -> BaseCheckpointSaver:
    """创建开发环境 Checkpointer / Create dev checkpointer.

    开发用内存存储，不持久化到磁盘。
    Development uses in-memory storage, no disk persistence.
    """
    return create_checkpointer("memory")


def create_sqlite_checkpointer(conn_string: str) -> BaseCheckpointSaver:
    """创建 SQLite Checkpointer / Create SQLite checkpointer.

    Args:
        conn_string: SQLite 连接串，如 "sqlite:///data/checkpoints.db"

    Returns:
        BaseCheckpointSaver: SQLite-backed checkpointer
    """
    return create_checkpointer("sqlite", conn_string=conn_string)


def create_postgres_checkpointer(conn_string: str) -> BaseCheckpointSaver:
    """创建 PostgreSQL Checkpointer / Create PostgreSQL checkpointer.

    Args:
        conn_string: PostgreSQL 连接串，如 "postgresql://user:pass@host/db"

    Returns:
        BaseCheckpointSaver: PostgreSQL-backed checkpointer
    """
    return create_checkpointer("postgres", conn_string=conn_string)


def create_redis_checkpointer(redis_url: str) -> BaseCheckpointSaver:
    """创建 Redis Checkpointer / Create Redis checkpointer.

    Args:
        redis_url: Redis 连接 URL，如 "redis://localhost:6379/0"

    Returns:
        BaseCheckpointSaver: Redis-backed checkpointer
    """
    return create_checkpointer("redis", redis_url=redis_url)


