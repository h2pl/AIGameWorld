"""测试全局配置 / Test global configuration.

- 禁用 LangSmith/Langfuse tracing，避免测试 trace 污染监控面板
- 提供 mock_repos fixture 和 _make_mock_llm() 供 integration/e2e 测试使用
"""

import os
from unittest.mock import AsyncMock

import pytest

# 禁用 tracing（必须在任何 src 模块 import 之前执行） / Disable tracing before importing src
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGFUSE_ENABLED"] = "false"


# ═══════════════════════════════════════════════════════════════
# Mock LLM
# ═══════════════════════════════════════════════════════════════


class _MockLLM:
    """轻量 mock LLM——从 mock_data.py 返回数据，不调用真实 LLM。

    与 LLMClient 接口兼容：call / call_structured / set_context / _mock
    """

    _mock = True
    _mock_dataset = "tavern"
    _metrics_collector = None
    _current_world_id = ""

    def set_context(self, world_id: str) -> None:
        self._current_world_id = world_id

    async def call(self, purpose: str, tick_messages, **kwargs):
        from src.llm.mock_data import get_mock

        data = get_mock(purpose, self._mock_dataset)
        return data.get("narrative", data.get("summary", str(data)))

    async def call_structured(self, purpose: str, schema, tick_messages, fallback=None, **kwargs):
        from src.llm.mock_data import get_mock

        data = get_mock(purpose, self._mock_dataset)
        try:
            return schema(**data)
        except Exception:
            if fallback:
                return fallback()
            raise


def _make_mock_llm():
    """创建 mock LLM 实例 / Create a mock LLM instance."""
    return _MockLLM()


# ═══════════════════════════════════════════════════════════════
# mock_repos fixture
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def mock_repos(tmp_path):
    """真实 SQLite 内存 DB + mock LLM + seed 测试数据 / Real SQLite + mock LLM + seed data.

    返回 dict，含所有 repo + "llm" 键，可直接传给 Orchestrator。
    """
    from src.domain import PlayerCharacter, Scene, World
    from src.repository.actor_repo import ActorRepo
    from src.repository.dm_record_repo import DMRecordRepo
    from src.repository.event_repo import TickEventRepo
    from src.repository.pc_repo import PcRepo
    from src.repository.scene_repo import SceneRepo
    from src.repository.world_repo import WorldRepo
    from src.storage.sqlite_client import SQLiteClient

    db = SQLiteClient(str(tmp_path / "test.db"))
    await db.connect()
    await db.init_schema()

    # memory_repo 用 AsyncMock 避免依赖 chromadb / Mock memory_repo to avoid chromadb dependency
    memory_repo = AsyncMock()
    memory_repo.retrieve = AsyncMock(return_value=[])
    memory_repo.store = AsyncMock(return_value=None)
    memory_repo.initialize = AsyncMock(return_value=None)

    repos = {
        "world": WorldRepo(db),
        "char": PcRepo(db),
        "actor": ActorRepo(db),
        "scene": SceneRepo(db),
        "memory": memory_repo,
        "event": TickEventRepo(db),
        "dm_record": DMRecordRepo(db),
        "llm": _make_mock_llm(),
    }

    # Seed 测试数据 / Seed test data
    await repos["world"].create(World(id="test", name="Test World"))
    await repos["scene"].save_scene(
        Scene(
            id="tavern",
            name="Tavern",
            type="indoor",
            description="A cozy tavern.",
            spawn_x=10,
            spawn_y=10,
            map_width=40,
            map_height=40,
        ),
        world_id="test",
    )
    await repos["char"].save(
        PlayerCharacter(
            id="pc-1",
            name="Hero",
            role="fighter",
            scene_id="tavern",
            world_id="test",
        )
    )

    yield repos

    await db.close()
