"""DM Engine——LLM 驱动的情境创造与叙事。per design/04-agent-layer.md §5.

分层遵循 Service → Engine → Repository 调用链：
Service 负责 State↔Request 适配，Engine 负责业务逻辑 + 从 config 取 repos 调用 Repository。
"""

import json
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...domain import (
    Action,
    Actor,
    DMRecord,
    PlayerCharacter,
    Scene,
    SceneObject,
    TickEvent,
    World,
)
from ...schemas.llm_output import DMNarrativeSchema, DMOutput
from ...services.memory_service import retrieve_dm_records
from ...utils.helpers import get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


async def dm_create(
    tick: int,
    world_id: str = "",
    plot_brief: str = "",
    prev_narrative: str = "",
    config: RunnableConfig = None,
) -> DMRecord:
    """Phase 1: DM 创造情境 / DM creates situation."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_create] LLM client not configured")

    scene_repo = get_repo(config, "scene")
    scenes: list[SimpleNamespace] = []
    scene_objects_by_scene: dict[str, list[SceneObject]] = {}
    if scene_repo and world_id:
        raw_scenes = await scene_repo.list_scenes(world_id)
        all_objects = await scene_repo.list_objects_by_world(world_id)
        for obj in all_objects:
            scene_obj = SceneObject(**obj)
            scene_objects_by_scene.setdefault(scene_obj.scene_id, []).append(scene_obj)
        scenes = [_enrich_scene(s, scene_objects_by_scene.get(s.id, [])) for s in raw_scenes]

    # 检索 DM 记忆（复用 dm_records）/ Retrieve DM memories from dm_records
    memories: list[str] = []
    try:
        mems = await retrieve_dm_records(world_id or "", config=config, top_k=5, before_tick=tick)
        memories = list(mems) if mems else []
    except Exception:
        logger.warning("[engine] dm_create memory retrieval failed, continuing without memories")

    # 检索 World Pack 知识 / Retrieve World Pack knowledge
    world_knowledge = ""
    try:
        knowledge_repo = get_repo(config, "knowledge")
        if knowledge_repo:
            world_knowledge = knowledge_repo.retrieve_for_purpose(
                purpose="dm_create",
                query=plot_brief or prev_narrative or world_id or "",
                top_k=3,
            )
    except Exception:
        logger.warning(
            "[engine] dm_create knowledge retrieval failed, continuing without knowledge"
        )

    logger.info("[engine] dm_create tick=%s world=%s", tick, world_id or "-")
    system_prompt = await _render_dm_system(config, world_id)
    prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
        scenes=scenes,
        recent_summary="",
        plot_brief_prev=plot_brief,
        prev_narrative=prev_narrative,
        memories=memories,
        world_knowledge=world_knowledge,
        pacing={},
    )
    result = await llm.call_structured(
        "dm_create",
        DMOutput,
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
    )
    if len(result.hints) > 4:
        result.hints = result.hints[:4]

    return DMRecord(
        world_id=world_id,
        tick=tick,
        plot_brief=result.plot_brief,
        hints=result.hints,
        scene_id=result.scene_id,
        ext=result.model_dump(),
    )


async def dm_narrate(
    tick: int,
    world_id: str,
    plot_brief: str,
    hints: list[str],
    events: list[TickEvent],
    scene: Scene,
    scene_objects: list[SceneObject],
    pcs: dict[str, PlayerCharacter],
    actors: dict[str, Actor],
    actions: list[Action],
    prev_narrative: str = "",
    config: RunnableConfig = None,
) -> str:
    """Phase 6: DM 叙事 / DM narrates."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_narrate] LLM client not configured")

    # 检索 DM 记忆（复用 dm_records）
    dm_memories: list[str] = []
    try:
        mems = await retrieve_dm_records(world_id or "", config=config, top_k=3, before_tick=tick)
        dm_memories = list(mems) if mems else []
    except Exception:
        logger.warning("[engine] dm_narrate memory retrieval failed, continuing without memories")

    # 检索 World Pack 知识 / Retrieve World Pack knowledge
    world_knowledge = ""
    try:
        knowledge_repo = get_repo(config, "knowledge")
        if knowledge_repo:
            world_knowledge = knowledge_repo.retrieve_for_purpose(
                purpose="dm_narrate",
                query=(plot_brief or (scene.description if scene else None) or world_id or ""),
                top_k=3,
            )
    except Exception:
        logger.warning(
            "[engine] dm_narrate knowledge retrieval failed, continuing without knowledge"
        )

    system_prompt = await _render_dm_system(config, world_id)
    prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
        tick=tick,
        plot_brief=plot_brief,
        hints=hints,
        scene=scene,
        scene_objects=scene_objects,
        pcs=list(pcs.values()),
        actors=list(actors.values()),
        events=_event_summaries(events),
        actions=actions,
        prev_narrative=prev_narrative,
        memories=dm_memories,
        world_knowledge=world_knowledge,
    )

    result = await llm.call_structured(
        "dm_narrate",
        DMNarrativeSchema,
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
    )

    narrative = (result.narrative or "").strip()
    if not narrative:
        logger.error(
            "[engine] dm_narrate produced empty narrative; tick=%s prompt_preview=%s",
            tick,
            prompt[:1200],
        )
        raise RuntimeError(f"[dm_narrate] LLM returned empty narrative at tick={tick}")

    logger.info("[engine] dm_narrate tick=%s narrative_len=%s", tick, len(narrative))
    return narrative


def _event_summaries(events: list[TickEvent] | None) -> list[str]:
    """把 TickEvent 列表转成 prompt 可读的摘要 / Summarize events for prompt.

    提供结构化的中文摘要，避免原始 JSON 进入 prompt。
    """
    # 事件类型中文标签映射 / Chinese labels for event types
    _TYPE_LABELS: dict[str, str] = {
        "dm_create": "DM 创造情境",
        "dm_narrative": "DM 叙事",
        "pc_decision": "角色决策",
        "pc_talk": "角色对话",
        "pc_explore": "角色探索",
        "pc_interact": "角色互动",
        "pc_combat": "角色战斗",
        "scene_setup": "场景设置",
        "character_move": "角色移动",
    }
    summaries: list[str] = []
    for ev in events or []:
        ev_type = ev.type.value if hasattr(ev.type, "value") else str(ev.type)
        label = _TYPE_LABELS.get(ev_type, ev_type)
        p = ev.payload or {}
        # 提取角色名称 / Extract character name
        pc_name = str(p.get("pc_name") or p.get("pc_id") or "")

        # 决策事件：提取行动类型、目标和理由 / Decision: action type, target, reason
        if ev_type == "pc_decision":
            action = str(p.get("action_type") or "wait")
            target = p.get("target_id")
            reason = str(p.get("thought") or "")[:60]
            target_str = f"与 {target}" if target else ""
            summaries.append(f"{pc_name} 决定{target_str}{action} — {reason}")

        # 对话事件：提取对话回合预览 / Talk: dialogue turns preview
        elif ev_type == "pc_talk":
            turns = (
                p.get("result", {}).get("turns", []) if isinstance(p.get("result"), dict) else []
            )
            target = p.get("target_id", "他人")
            preview = " / ".join(t.get("text", "")[:20] for t in turns[:4]) if turns else ""
            summaries.append(f"{pc_name} 与 {target} 对话：{preview}")

        # 探索事件 / Explore event
        elif ev_type == "pc_explore":
            record = str(p.get("explore_record") or "四处探索")[:60]
            summaries.append(f"{pc_name} 探索：{record}")

        # 交互事件 / Interact event
        elif ev_type == "pc_interact":
            target = p.get("target_id", "物体")
            narration = str(p.get("narration") or "")[:60]
            summaries.append(f"{pc_name} 与 {target} 交互：{narration}")

        # 战斗事件：含击败标记 / Combat event with defeated flag
        elif ev_type == "pc_combat":
            target = p.get("target_id", "敌人")
            narration = str(p.get("narration") or "")[:60]
            defeated = "，击败目标" if p.get("target_defeated") else ""
            summaries.append(f"{pc_name} 与 {target} 战斗：{narration}{defeated}")

        # DM 创建情境 / DM creation event
        elif ev_type == "dm_create":
            brief = str(p.get("plot_brief") or "")[:80]
            summaries.append(f"情境设定：{brief}")

        # 其他事件：截断原始 payload / Other: truncated raw payload
        else:
            description = str(p)[:120] if p else ""
            summaries.append(f"{label}：{description}")

    return summaries


async def _render_dm_system(config: RunnableConfig | None, world_id: str) -> str:
    """渲染 DM system prompt，注入世界观信息 / Render DM system prompt with world info."""
    world: World | None = None
    if world_id:
        world_repo = get_repo(config, "world")
        if world_repo:
            world = await world_repo.get(world_id)
    return _PROMPTS.get_template("dm/_dm_system.jinja").render(world=world)


def _enrich_scene(scene: Scene, objects: list[SceneObject]) -> SimpleNamespace:
    """解析 ext_json 并补充场景物体信息 / Parse ext_json and attach scene objects."""
    ext: dict = {}
    if isinstance(scene.ext_json, str) and scene.ext_json.strip():
        try:
            ext = json.loads(scene.ext_json)
        except json.JSONDecodeError:
            ext = {}
    return SimpleNamespace(
        id=scene.id,
        name=scene.name,
        type=scene.type,
        description=scene.description,
        spawn_x=scene.spawn_x,
        spawn_y=scene.spawn_y,
        map_width=scene.map_width,
        map_height=scene.map_height,
        tilemap_summary=scene.tilemap_summary,
        environment=ext.get("environment", {}),
        objects=objects,
    )
