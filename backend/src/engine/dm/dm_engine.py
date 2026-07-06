"""DM Engine——LLM 驱动的情境创造与叙事。per design/04-agent-layer.md §5.

分层遵循 Service → Engine → Repository 调用链：
Service 负责 State↔Request 适配，Engine 负责业务逻辑 + 从 config 取 repos 调用 Repository。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import DMNarrativeSchema, DMOutput
from ...schemas.request import DMCreateRequest, DMNarrateRequest
from ...schemas.response import DMCreateResponse, DMNarrateResponse
from ...services.memory_service import retrieve_memories
from ...utils.helpers import get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
_DM_MEMORY_ID = "dm"  # DM 全局记忆 id


async def dm_create(
    req: DMCreateRequest,
    config: RunnableConfig = None,
) -> DMCreateResponse:
    """Phase 1: DM 创造情境 / DM creates situation."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_create] LLM client not configured")

    scene_repo = get_repo(config, "scene")
    scenes: list[dict] = []
    if scene_repo and req.world_id:
        scenes = await scene_repo.list_scenes(req.world_id)

    # 检索 DM 记忆 / Retrieve DM memories
    recent_summary = ""
    memories: list[str] = []
    try:
        mems = await retrieve_memories(
            _DM_MEMORY_ID, req.plot_brief or "recent", config=config, top_k=5
        )
        memories = list(mems) if mems else []
    except Exception:
        logger.warning("[engine] dm_create memory retrieval failed, continuing without memories")

    logger.info("[engine] dm_create tick=%s world=%s", req.tick, req.world_id or "-")
    system_prompt = await _render_dm_system(config, req.world_id)
    prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
        scenes=scenes,
        recent_summary=recent_summary,
        plot_brief_prev=req.plot_brief,
        memories=memories,
        pacing={},
    )
    result = await llm.call_structured(
        "dm_create",
        DMOutput,
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
    )
    if len(result.hints) > 4:
        result.hints = result.hints[:4]

    # 存入 DM 记忆 / Store DM memory
    await _store_dm_memory(req.world_id, req.tick, result.plot_brief, config)

    return DMCreateResponse(
        hints=result.hints,
        plot_brief=result.plot_brief,
        scene_id=result.scene_id,
        ext=result.model_dump(),
    )


async def dm_narrate(req: DMNarrateRequest, config: RunnableConfig = None) -> DMNarrateResponse:
    """Phase 6: DM 叙事 / DM narrates."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_narrate] LLM client not configured")

    # 检索 DM 记忆 / Retrieve DM memories
    memories: list[str] = []
    try:
        mems = await retrieve_memories(
            _DM_MEMORY_ID, req.plot_brief or "recent", config=config, top_k=3
        )
        memories = list(mems) if mems else []
    except Exception:
        logger.warning("[engine] dm_narrate memory retrieval failed, continuing without memories")

    system_prompt = await _render_dm_system(config, req.world_id)
    prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
        plot_brief=req.plot_brief,
        hints=req.hints,
        events=req.events,
        memories=memories,
    )
    result = await llm.call_structured(
        "dm_narrate",
        DMNarrativeSchema,
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
    )
    narrative = result.narrative
    logger.info("[engine] dm_narrate tick=%s narrative_len=%s", req.tick, len(narrative or ""))

    return DMNarrateResponse(narrative_out=narrative)


async def _render_dm_system(config: RunnableConfig | None, world_id: str) -> str:
    """渲染 DM system prompt，注入世界观信息 / Render DM system prompt with world info."""
    world = None
    if world_id:
        world_repo = get_repo(config, "world")
        if world_repo:
            w = await world_repo.get(world_id)
            if w:
                world = {"name": w.name, "description": w.description, "rule_set": w.rule_set}
    return _PROMPTS.get_template("dm/_dm_system.jinja").render(world=world)


async def _store_dm_memory(
    world_id: str,
    tick: int,
    plot_brief: str,
    config: RunnableConfig = None,
) -> None:
    """存入 DM 全局记忆 / Store DM global memory."""
    memory_repo = get_repo(config, "memory")
    if not memory_repo or not plot_brief:
        return
    await memory_repo.store(_DM_MEMORY_ID, f"[tick {tick}] {plot_brief}", tick, importance=5)
