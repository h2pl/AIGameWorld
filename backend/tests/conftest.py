"""共享 fixtures——per 11-testing-strategy.md §3.

测试使用独立 DB（config.yaml database.test_sqlite_path），不影响生产数据。
"""

from pathlib import Path

import pytest

from src.graph.state import OverallState

# 测试 DB 路径 / Test database path
_TEST_DIR = Path(__file__).parent / "data"
_TEST_DB = _TEST_DIR / "test.db"


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """测试专用 DB 路径 / Test database path."""
    _TEST_DIR.mkdir(exist_ok=True)
    # 从 config 读取，失败时用默认值
    try:
        from src.config import load_config

        config = load_config(str(Path(__file__).parent.parent / "config.yaml"))
        db_path = Path(config.database.test_sqlite_path)
        if not db_path.is_absolute():
            db_path = Path(__file__).parent.parent / db_path
    except Exception:
        db_path = _TEST_DB
    return db_path


@pytest.fixture(scope="session")
def seed_db(test_db_path: Path):
    """创建并初始化测试 DB / Create and init test database."""
    test_db_path.parent.mkdir(exist_ok=True)
    import sqlite3

    schema = Path(__file__).parent.parent / "src" / "storage" / "schema.sql"
    conn = sqlite3.connect(str(test_db_path))
    conn.executescript(schema.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    yield test_db_path
    # 清理 / Cleanup
    if test_db_path.exists():
        test_db_path.unlink(missing_ok=True)


@pytest.fixture
def base_state() -> OverallState:
    """基础 mock state."""
    return OverallState(
        tick=0,
        world_id="",
        tick_message_id="",
        scene_info={},
        pending_actions=[],
        hints=[],
        plot_brief="",
        scene_id="",
        pc_decisions=[],
        narrative="",
    )
