"""Graph Checkpoints 测试——创建、验证."""

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.graph.checkpoints import (
    create_checkpointer,
    create_dev_checkpointer,
    create_postgres_checkpointer,
    create_redis_checkpointer,
    create_sqlite_checkpointer,
)


class TestCreateCheckpointer:
    def test_memory_saver(self):
        cp = create_checkpointer("memory")
        assert isinstance(cp, MemorySaver)

    @pytest.mark.skip(reason="langgraph.checkpoint.sqlite not installed")
    def test_sqlite_saver(self):
        cp = create_checkpointer("sqlite", conn_string=":memory:")
        assert cp is not None

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported saver_type"):
            create_checkpointer("mongodb")  # type: ignore

    def test_create_dev_checkpointer(self):
        cp = create_dev_checkpointer()
        assert isinstance(cp, MemorySaver)

    @pytest.mark.skip(reason="langgraph.checkpoint.sqlite not installed")
    def test_create_sqlite_checkpointer(self):
        cp = create_sqlite_checkpointer(":memory:")
        assert cp is not None


# postgres/redis 需要对应依赖，跳过集成测试
class TestPostgresRedisCheckpointer:
    @pytest.mark.skip(reason="Requires psycopg dependency")
    def test_postgres_saver(self):
        cp = create_postgres_checkpointer("postgresql://localhost/test")
        assert cp is not None

    @pytest.mark.skip(reason="Requires redis dependency")
    def test_redis_saver(self):
        cp = create_redis_checkpointer("redis://localhost:6379/0")
        assert cp is not None
