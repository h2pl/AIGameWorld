"""FastAPI 应用入口 / App entry point.

World CRUD + Tick 执行 + DB Viewer.
Orchestrator 直接驱动 graph，无后台任务 / Orchestrator drives graph directly, no background tasks.

所有业务路由已拆分到 src/api/ 下，本文件只负责：
- 应用创建与生命周期
- CORS 中间件
- 路由注册
- 日志配置
"""

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.eval import router as eval_router
from src.api.events import router as events_router
from src.api.health import router as health_router
from src.api.metrics import router as metrics_router
from src.api.mock import router as mock_router
from src.api.reset import router as reset_router
from src.api.scene import router as scene_router
from src.api.state import router as state_router
from src.api.tick import router as tick_router
from src.api.view import router as view_router
from src.api.world import router as world_router
from src.api.world_eval import router as world_eval_router
from src.storage.sqlite_client import SQLiteClient
from src.utils.logging import configure_format, get_logger, setup_logging

logger = get_logger(__name__)

# ── 预加载配置，供 lifespan 使用 / Preload config for lifespan use ──
try:
    from .config import load_config

    _config_path = os.environ.get("AIGW_CONFIG", "../config.yaml")
    _pre_cfg = load_config(_config_path)
    configure_format(_pre_cfg.logging.json_format)
    # 不在模块级 setup_logging，避免与 uvicorn handler 冲突
    # defer logging setup to lifespan, after uvicorn has initialized its own
except Exception:
    _pre_cfg = None

# FastAPI 应用实例 / FastAPI app instance
app = FastAPI(title="AIGameWorld API", version="0.1.0")


@app.middleware("http")
async def trace_middleware(request, call_next):
    """链路追踪中间件：传播 trace_id / Trace middleware: propagate trace_id."""
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化日志、DB、mock 数据、编排器."""
    from .config import load_config

    cfg = _pre_cfg or load_config(os.environ.get("AIGW_CONFIG", "../config.yaml"))

    # ── 日志：在 uvicorn 启动后完全接管，避免 handler 冲突 / Take over logging after uvicorn startup ──
    setup_logging(
        cfg.logging.level,
        json_fmt=cfg.logging.json_format,
        rotation=cfg.logging.rotation,
    )

    logger.info(
        "[lifespan] logging configured level=%s json=%s rotation=%s",
        cfg.logging.level,
        cfg.logging.json_format,
        cfg.logging.rotation.when,
    )
    # ── DB ──
    db_path = cfg.db_name
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
    from .repository.knowledge_repo import KnowledgeRepo
    from .repository.memory_repo import MemoryRepo
    from .repository.pc_repo import PcRepo
    from .repository.scene_repo import SceneRepo
    from .repository.world_repo import WorldRepo
    from .storage.chroma_client import ChromaClient

    llm = LLMClient(cfg)
    # 向量存储：根据配置选择嵌入模型 / Vector store: select embedding model from config
    embedding_model = cfg.database.embedding_model
    if embedding_model == "bge-m3":
        chroma = ChromaClient.create_with_bge_m3(Path(__file__).parent.parent / "data" / "chroma")
    else:
        chroma = ChromaClient(Path(__file__).parent.parent / "data" / "chroma")
    memory_repo = MemoryRepo(chroma=chroma, sqlite=db)
    await memory_repo.initialize()

    # World Pack 知识库 / World Pack knowledge base
    knowledge_repo = KnowledgeRepo(chroma=chroma)
    # 索引默认 World Pack / Index default World Pack
    default_pack = cfg.world.default_pack
    pack_path = Path(__file__).parent.parent.parent / "world-pack" / default_pack
    await knowledge_repo.index_pack(pack_path, default_pack)

    # 指标收集器 / Metrics collector
    from src.utils.metrics import MetricsCollector

    model_name = getattr(cfg.llm, "dm_create", None)
    model_name = model_name.model if model_name else "default"
    metrics_collector = MetricsCollector(sqlite=db, model=model_name)
    await metrics_collector.initialize()
    app.state.metrics_collector = metrics_collector

    # LangSmith 开发期追踪 / LangSmith dev-time tracing
    from src.utils.tracing import configure_langsmith, is_langsmith_enabled

    if is_langsmith_enabled():
        configure_langsmith()
        logger.info("[server] LangSmith tracing enabled")

    # 评估存储 / Evaluation store
    from src.eval.eval_store import EvalStore

    eval_store = EvalStore(sqlite=db)
    await eval_store.initialize()
    app.state.eval_store = eval_store

    # 游戏世界状态评估器 / Game world state evaluator
    from src.eval.world_state_evaluator import WorldStateEvaluator

    world_evaluator = WorldStateEvaluator()
    app.state.world_evaluator = world_evaluator

    # LangSmith 评估桥接 / LangSmith eval bridge
    if is_langsmith_enabled():
        from src.eval.langsmith_runner import create_langsmith_eval_config

        eval_config = create_langsmith_eval_config()
        if eval_config:
            app.state.langsmith_eval_config = eval_config
            logger.info(
                "[server] LangSmith eval bridge configured: %s", eval_config.get("project_name")
            )

    repos = {
        "char": PcRepo(db),
        "actor": ActorRepo(db),
        "dm_record": DMRecordRepo(db),
        "scene": SceneRepo(db),
        "world": WorldRepo(db),
        "event": TickEventRepo(db),
        "memory": memory_repo,
        "knowledge": knowledge_repo,
    }
    app.state.repos = repos

    app.state.orchestrator = Orchestrator(
        llm=llm,
        repos=repos,
        metrics_collector=metrics_collector,
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
app.include_router(metrics_router)
app.include_router(eval_router)
app.include_router(world_eval_router)
