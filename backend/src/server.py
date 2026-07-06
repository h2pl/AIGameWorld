"""FastAPI 应用入口 / App entry point.

World CRUD + Tick 执行 + DB Viewer.
Orchestrator 直接驱动 graph，无后台任务 / Orchestrator drives graph directly, no background tasks.

所有业务路由已拆分到 src/api/ 下，本文件只负责：
- 应用创建与生命周期
- CORS 中间件
- 路由注册
- 日志配置
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.events import router as events_router
from src.api.health import router as health_router
from src.api.mock import router as mock_router
from src.api.reset import router as reset_router
from src.api.scene import router as scene_router
from src.api.state import router as state_router
from src.api.tick import router as tick_router
from src.api.view import router as view_router
from src.api.world import router as world_router
from src.storage.sqlite_client import SQLiteClient
from src.utils.logging import configure_console, configure_format, get_logger, setup_logging

logger = get_logger(__name__)

# 在应用创建前初始化日志 / Initialize logging before app creation
try:
    from .config import load_config

    _cfg = load_config("../config.yaml")
    configure_format(_cfg.logging.json_format)
    setup_logging(_cfg.logging.level)
    configure_console(_cfg.logging.console.model_dump())
except Exception:
    setup_logging()
    configure_console(None)

# FastAPI 应用实例 / FastAPI app instance
app = FastAPI(title="AIGameWorld API", version="0.1.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化 DB、mock 数据、编排器 / App lifespan: init DB, mock data, orchestrator."""
    from .config import load_config

    cfg = load_config("../config.yaml")
    db_path = cfg.db_name
    # 创建并连接 SQLite / Create and connect SQLite
    db = SQLiteClient(db_path)
    app.state.db = db
    await db.connect()
    await db.init_schema()
    logger.info("[lifespan] db=%s ready", db_path)

    # mock 模式下注入 mock 数据 / Seed mock data if in mock mode
    if cfg.data_mode == "mock":
        from data.mock import seed_mock_data

        try:
            await seed_mock_data(db)
            logger.info("[lifespan] mock data seeded into %s", db_path)
        except Exception as exc:
            logger.warning("[lifespan] mock seed skipped: %s", exc)

    # 初始化 LLM 与编排器 / Init LLM client and orchestrator
    from .llm.llm_client import LLMClient
    from .orchestrator import Orchestrator
    from .repository.actor_repo import ActorRepo
    from .repository.dm_record_repo import DMRecordRepo
    from .repository.event_repo import TickEventRepo
    from .repository.memory_repo import MemoryRepo
    from .repository.pc_repo import PcRepo
    from .repository.scene_repo import SceneRepo
    from .repository.world_repo import WorldRepo
    from .storage.chroma_client import ChromaClient

    llm = LLMClient(cfg)
    chroma = ChromaClient(Path(__file__).parent.parent / "data" / "chroma")
    memory_repo = MemoryRepo(chroma=chroma, sqlite=db)
    await memory_repo.initialize()
    app.state.orchestrator = Orchestrator(
        llm=llm,
        repos={
            "char": PcRepo(db),
            "actor": ActorRepo(db),
            "dm_record": DMRecordRepo(db),
            "scene": SceneRepo(db),
            "world": WorldRepo(db),
            "event": TickEventRepo(db),
            "memory": memory_repo,
        },
    )
    logger.info("[lifespan] orchestrator ready")

    yield

    # 关闭资源 / Cleanup resources
    if app.state.orchestrator:
        app.state.orchestrator = None
    if app.state.db:
        await app.state.db.close()
        app.state.db = None


app.router.lifespan_context = lifespan
# 允许跨域 / Enable CORS for frontend
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 注册 API 路由 / Register API routers ──
app.include_router(world_router)
app.include_router(tick_router)
app.include_router(events_router)
app.include_router(reset_router)
app.include_router(scene_router)
app.include_router(state_router)
app.include_router(health_router)
app.include_router(view_router)
app.include_router(mock_router)
