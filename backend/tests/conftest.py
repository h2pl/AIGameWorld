"""共享 fixtures——per 11-testing-strategy.md §3.

测试使用独立 DB（config.yaml database.test_sqlite_path），不影响生产数据。
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.domain import Scene
from src.graph.state import OverallState

_TEST_DIR = Path(__file__).parent / "data"
_TEST_DB = _TEST_DIR / "test.db"


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """测试专用 DB 路径 / Test database path."""
    _TEST_DIR.mkdir(exist_ok=True)
    try:
        from src.config import load_config

        config = load_config(str(Path(__file__).parent.parent / "config.yaml"))
        db_path = Path(config.db_name)
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
    if test_db_path.exists():
        test_db_path.unlink(missing_ok=True)


@pytest.fixture
def base_state() -> OverallState:
    """基础 mock state / Base mock state."""
    return {
        "tick": 0,
        "world_id": "",
        "scene": Scene(id=""),
        "actions": [],
        "hints": [],
        "plot_brief": "",
        "scene_id": "",
        "pc_decisions": [],
        "narrative": "",
    }


def _make_mock_llm():
    """构造按 purpose 返回对应 schema 的 mock LLM."""
    from src.schemas.llm_output import (
        CombatNarrationSchema,
        DialogueSchema,
        DMNarrativeSchema,
        DMOutput,
        ExploreOutputSchema,
        InteractOutputSchema,
        PCDecideSchema,
        ReflectionOutputSchema,
        SummaryOutputSchema,
    )

    def _structured_side_effect(purpose: str, schema, messages):
        if purpose == "dm_create":
            return DMOutput(plot_brief="测试剧情", hints=["测试提示"], scene_id="tavern")
        if purpose == "dm_narrate":
            return DMNarrativeSchema(narrative="夜幕降临，酒馆里灯火通明。")
        if purpose == "pc_decision":
            return PCDecideSchema(
                action={
                    "action_type": "wait",
                    "target_id": None,
                    "target_type": None,
                    "thought": "等待时机。",
                }
            )
        if purpose == "talk":
            return DialogueSchema(turns=[])
        if purpose == "interact":
            return InteractOutputSchema(success=True, narration="交互成功。")
        if purpose == "explore":
            return ExploreOutputSchema(end_x=5, end_y=5, explore_record="发现了一条小路。")
        if purpose == "combat":
            return CombatNarrationSchema(
                narration="他挥剑击中敌人，战斗激烈。",
                target_defeated=True,
                result="目标被击败",
            )
        if purpose.startswith("reflect_"):
            return ReflectionOutputSchema(arc_analysis="弧线分析", personality_insight="性格洞察")
        if purpose == "summarize":
            return SummaryOutputSchema(summary="无事发生。")
        # 兜底：返回 schema 默认实例 / Fallback: return schema default instance
        return schema()

    llm = AsyncMock()
    llm.call = AsyncMock(return_value="mock response")
    llm.call_structured = AsyncMock(side_effect=_structured_side_effect)
    return llm


@pytest.fixture
def mock_llm():
    """按 purpose 返回对应 schema 的 mock LLM."""
    return _make_mock_llm()


@pytest.fixture
def mock_repos(mock_llm):
    """包含完整 mock repo + LLM 的字典，用于 Orchestrator 集成测试."""
    ticks = {}

    async def _increment_data_tick(world_id: str) -> int:
        ticks[world_id] = ticks.get(world_id, 0) + 1
        return ticks[world_id]

    async def _reset_tick(world_id: str) -> None:
        ticks[world_id] = 0

    world_repo = AsyncMock()
    world_repo.increment_data_tick = AsyncMock(side_effect=_increment_data_tick)
    world_repo.reset_tick = AsyncMock(side_effect=_reset_tick)
    world_repo.get = AsyncMock(return_value=None)

    pc_repo = AsyncMock()
    pc_repo.load_all = AsyncMock(return_value=[])
    pc_repo.load_one = AsyncMock(return_value=None)
    pc_repo.save = AsyncMock(return_value=None)

    actor_repo = AsyncMock()
    actor_repo.load_all = AsyncMock(return_value=[])
    actor_repo.load_one = AsyncMock(return_value=None)
    actor_repo.save = AsyncMock(return_value=None)

    scene_repo = AsyncMock()
    scene_repo.get_scene = AsyncMock(
        return_value=Scene(
            id="tavern",
            name="Tavern",
            type="indoor",
            description="一个热闹的酒馆。",
            spawn_x=10,
            spawn_y=10,
            map_width=40,
            map_height=40,
        )
    )
    scene_repo.get_object_ids = AsyncMock(return_value=[])
    scene_repo.load_all = AsyncMock(return_value={})
    scene_repo.list_scenes = AsyncMock(return_value=[])

    memory_repo = AsyncMock()
    memory_repo.store = AsyncMock(return_value=None)
    memory_repo.retrieve = AsyncMock(return_value=[])
    memory_repo._short_queue = AsyncMock(return_value=[])
    memory_repo.retrieve_reflections = AsyncMock(return_value=[])
    memory_repo.store_reflection = AsyncMock(return_value=None)

    event_repo = AsyncMock()
    event_repo.insert_batch = AsyncMock(return_value=None)
    event_repo.load_by_tick_range = AsyncMock(return_value=[])

    dm_record_repo = AsyncMock()
    dm_record_repo.save_plot_brief = AsyncMock(return_value=None)
    dm_record_repo.update_narrative = AsyncMock(return_value=None)

    return {
        "llm": mock_llm,
        "world": world_repo,
        "char": pc_repo,
        "actor": actor_repo,
        "scene": scene_repo,
        "memory": memory_repo,
        "event": event_repo,
        "dm_record": dm_record_repo,
    }
