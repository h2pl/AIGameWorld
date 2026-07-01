"""DM Engine——LLM 驱动的情境创造与叙事。per design/04-agent-layer.md §5.

分层遵循 Service → Engine → Repository 调用链：
Service 负责 State↔Request 适配，Engine 负责业务逻辑 + 从 config 取 repos 调用 Repository。
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...domain.dm_record import DMRecord
from ...schemas.llm_output import DMNarrativeSchema, DMOutput
from ...schemas.request import DMCreateRequest, DMNarrateRequest
from ...schemas.response import DMCreateResponse, DMNarrateResponse
from ...utils.helpers import get_llm, get_repo

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


async def dm_create(
    req: DMCreateRequest,
    config: RunnableConfig = None,
) -> DMCreateResponse:
    """Phase 1: DM 创造情境."""
    llm = get_llm(config)

    if llm is None:
        return DMCreateResponse(hints=[], plot_brief="平静的一天，没有特别事件。")

    scene_repo = get_repo(config, "scene")
    scenes: list[dict] = []
    if scene_repo and req.world_id:
        scenes = await scene_repo.list_scenes(req.world_id)

    try:
        system_prompt = await _render_dm_system(config, req.world_id)
        prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
            scenes=scenes,
            recent_summary="",
            plot_brief_prev=req.plot_brief,
            pacing={},
        )
        result = await llm.call_structured(
            "dm_create",
            DMOutput,
            [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
            fallback=lambda: DMOutput(
                hints=[],
                plot_brief="平静的一天，没有特别事件。",
            ),
        )
        if len(result.hints) > 4:
            result.hints = result.hints[:4]

        # scene_object_ids 由后端根据 scene_id 解析
        scene_id = result.scene_id
        scene_object_ids = await _get_objects_for_scene(scene_repo, scene_id) if scene_repo else []

        # 写入 dm_records
        record_repo = get_repo(config, "dm_record")
        if record_repo and req.world_id:
            await record_repo.save_plot_brief(
                DMRecord(
                    world_id=req.world_id,
                    tick=req.tick,
                    plot_brief=result.plot_brief,
                    hints=result.hints,
                    ext=result.model_dump(),
                )
            )
            logger.info("[dm_create] saved to dm_records tick=%s", req.tick)

        return DMCreateResponse(
            hints=result.hints,
            plot_brief=result.plot_brief,
            scene={"scene_id": scene_id, "scene_object_ids": scene_object_ids},
        )
    except Exception:
        logger.exception("dm_create failed, using fallback")
        return DMCreateResponse(
            hints=[],
            plot_brief="平静的一天，没有特别事件。",
            scene={},
            errors=["dm_create LLM 调用失败，使用降级输出"],
        )


async def dm_narrate(req: DMNarrateRequest, config: RunnableConfig = None) -> DMNarrateResponse:
    """Phase 6: DM 叙事，产出写入 dm_records."""
    llm = get_llm(config)

    if llm is None:
        return DMNarrateResponse(narrative_out="（DM 沉默了...）")
    try:
        system_prompt = await _render_dm_system(config, req.world_id)
        prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief=req.plot_brief,
            hints=req.hints,
            events=req.events,
        )
        result = await llm.call_structured(
            "dm_narrate",
            DMNarrativeSchema,
            [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
            fallback=lambda: DMNarrativeSchema(narrative="（DM 沉默了...）"),
        )
        narrative = result.narrative
        if not narrative or not narrative.strip():
            narrative = "（DM 沉默了...）"
        logger.info("[dm_narrate] tick=%s narrative_len=%s", req.tick, len(narrative))

        record_repo = get_repo(config, "dm_record")
        if record_repo:
            await record_repo.update_narrative(
                DMRecord(
                    world_id=req.world_id,
                    tick=req.tick,
                    dm_narrative=narrative,
                    ext={"narrative": narrative},
                )
            )
            logger.info("[dm_narrate] updated narrative in dm_records tick=%s", req.tick)

        return DMNarrateResponse(narrative_out=narrative)
    except Exception:
        logger.exception("dm_narrate failed, using fallback")
        return DMNarrateResponse(
            narrative_out="（DM 沉默了...）", errors=["dm_narrate LLM 调用失败，使用降级输出"]
        )


async def _render_dm_system(config: RunnableConfig | None, world_id: str) -> str:
    """渲染 DM system prompt，注入世界观信息."""
    world = None
    if world_id:
        world_repo = get_repo(config, "world")
        if world_repo:
            w = await world_repo.get(world_id)
            if w:
                world = {"name": w.name, "description": w.description, "rule_set": w.rule_set}
    return _PROMPTS.get_template("_dm_system.jinja").render(world=world)


async def _get_objects_for_scene(scene_repo, scene_id: str) -> list[str]:
    """根据 scene_id 查找关联的场景对象 id 列表."""
    if not scene_id or not scene_repo:
        return []
    return await scene_repo.get_object_ids(scene_id)
