"""世界状态评估 API / World state evaluation API routes."""

from fastapi import APIRouter, Query, Request

from src.eval.world_state_evaluator import WorldStateEvaluator
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/eval/world", tags=["world-eval"])


def _get_evaluator(request: Request) -> WorldStateEvaluator | None:
    """从 app.state 获取 WorldStateEvaluator / Get evaluator from app.state."""
    return getattr(request.app.state, "world_evaluator", None)


def _to_dict_list(items: list) -> list[dict]:
    """将对象列表转为字典列表 / Convert object list to dict list."""
    return [dict(i) if hasattr(i, "__dict__") else i for i in items]


@router.get("/evaluate")
async def evaluate_current_state(
    world_id: str = Query("mock_world", description="世界 ID / World ID"),
    request: Request = None,
):
    """评估当前世界状态（多维度）/ Evaluate current world state across all dimensions."""
    evaluator = _get_evaluator(request)
    if not evaluator:
        return {"error": "world evaluator not initialized"}

    # 从后端获取当前状态 / Fetch current state from backend
    db = getattr(request.app.state, "db", None)
    if not db:
        return {"error": "database not available"}

    # 获取最新 tick 和实体 / Get latest tick and entities
    repos = getattr(request.app.state, "repos", {})
    world_repo = repos.get("world")
    pc_repo = repos.get("char")
    actor_repo = repos.get("actor")
    event_repo = repos.get("event")
    scene_repo = repos.get("scene")
    memory_repo = repos.get("memory")

    tick = 0
    pcs = []
    actors = []
    events = []
    scenes = []
    memories = []

    if world_repo:
        state = await world_repo.get_state(world_id)
        tick = state.get("data_tick", 0) if state else 0

    if pc_repo:
        pcs = await pc_repo.list_by_world(world_id)

    if actor_repo:
        actors = await actor_repo.list_by_world(world_id)

    if event_repo:
        events = await event_repo.list_by_tick(world_id, tick)

    if scene_repo:
        scenes = await scene_repo.list_by_world(world_id)

    if memory_repo:
        memories = await memory_repo.list_by_world(world_id, tick)

    report = evaluator.evaluate(
        tick=tick,
        world_id=world_id,
        pcs=_to_dict_list(pcs),
        actors=_to_dict_list(actors),
        events=_to_dict_list(events),
        scenes=_to_dict_list(scenes),
        memories=_to_dict_list(memories),
    )

    return report.to_dict()


@router.post("/run")
async def run_evaluation(
    request: Request,
    world_id: str = Query("mock_world", description="世界 ID / World ID"),
):
    """执行评估（LangSmith Runner 可调用）/ Run evaluation (callable by LangSmith Runner).

    LangSmith Scenario Dataset → LangSmith Runner → 此端点 → 自研 Evaluator → Score 返回 LangSmith
    """
    evaluator = _get_evaluator(request)
    if not evaluator:
        return {"error": "world evaluator not initialized"}

    db = getattr(request.app.state, "db", None)
    repos = getattr(request.app.state, "repos", {})
    if not db:
        return {"error": "database not available"}

    from src.eval.langsmith_runner import run_eval_with_langsmith

    # 获取当前 tick / Get current tick
    world_repo = repos.get("world")
    pc_repo = repos.get("char")
    actor_repo = repos.get("actor")
    event_repo = repos.get("event")
    scene_repo = repos.get("scene")
    memory_repo = repos.get("memory")

    tick = 0
    pcs = []
    actors = []
    events = []
    scenes = []
    memories = []

    if world_repo:
        state = await world_repo.get_state(world_id)
        tick = state.get("data_tick", 0) if state else 0

    if pc_repo:
        pcs_raw = await pc_repo.list_by_world(world_id)
        pcs = _to_dict_list(pcs_raw)

    if actor_repo:
        actors_raw = await actor_repo.list_by_world(world_id)
        actors = _to_dict_list(actors_raw)

    if event_repo:
        events_raw = await event_repo.list_by_tick(world_id, tick)
        events = _to_dict_list(events_raw)

    if scene_repo:
        scenes_raw = await scene_repo.list_by_world(world_id)
        scenes = _to_dict_list(scenes_raw)

    if memory_repo:
        memories_raw = await memory_repo.list_by_world(world_id, tick)
        memories = _to_dict_list(memories_raw)

    result = await run_eval_with_langsmith(
        world_id=world_id,
        tick=tick,
        evaluator=evaluator,
        pcs=pcs,
        actors=actors,
        events=events,
        scenes=scenes,
        memories=memories,
    )

    return result.to_dict()


@router.get("/history")
async def get_eval_history(
    world_id: str = Query("mock_world", description="世界 ID / World ID"),
    last_n: int = Query(20, description="最近 N 条 / Last N records"),
    request: Request = None,
):
    """获取评估历史 / Get evaluation history."""
    # 从 SQLite eval_results 表读取 / Read from SQLite eval_results table
    eval_store = getattr(request.app.state, "eval_store", None)
    if not eval_store:
        return {"history": [], "message": "eval store not initialized"}
    results = await eval_store.get_recent(dimension="world_state", last_n=last_n)
    return {"history": results}
