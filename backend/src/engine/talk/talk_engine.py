"""Talk Engine——处理角色交谈动作 / Handle character talk actions.

单次 LLM 调用生成双方多轮对话（turns 数组），返回 character_talk 事件供上层收集后统一落盘，
并把对话存入双方记忆。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import DialogueSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


async def process_talk_action(
    decision: dict,
    plot_brief: str,
    hints: list[str],
    scene_id: str,
    tick: int,
    pc_state_map: dict[str, dict] | None = None,
    actor_state_map: dict[str, dict] | None = None,
    config: RunnableConfig = None,
) -> dict | None:
    """处理单个 talk 决策 → 生成多轮对话，更新发起者坐标到目标旁边"""
    if decision.get("type") != "talk":
        return None

    char_id = decision.get("pc_id", "")
    target_id = decision.get("target_id", "")
    target_type = decision.get("target_type", "")
    reason = decision.get("description", "")

    turns = await _generate_dialogue(
        char_id, target_id, target_type, reason, plot_brief, hints, scene_id, config
    )
    if not turns:
        turns = [{"speaker_id": char_id, "text": reason or f"{char_id} 发起交谈。"}]
    else:
        turns = _normalize_speaker_ids(turns, char_id, target_id)

    await _store_dialogue_memory(char_id, target_id, turns, tick, config)

    waypoints = _update_talker_position(
        char_id, target_id, target_type, pc_state_map, actor_state_map
    )

    logger.info("[engine] %s ↔ %s : %d turns", char_id, target_id, len(turns))
    return {
        "kind": "pc_talk",
        "participants": [pid for pid in (char_id, target_id) if pid],
        "turns": turns,
        "waypoints": waypoints,
    }


async def _generate_dialogue(
    char_id: str,
    target_id: str,
    target_type: str,
    reason: str,
    plot_brief: str,
    hints: list[str],
    scene_id: str,
    config: RunnableConfig = None,
) -> list[dict]:
    """单次 LLM 调用生成双方多轮对话 / Generate a multi-turn dialogue in a single LLM call."""
    llm = get_llm(config)
    if not llm or not target_id:
        return []

    pc_repo = get_repo(config, "char")
    actor_repo = get_repo(config, "actor")
    initiator = await pc_repo.load_one(char_id) if pc_repo else None
    target = await _load_target(pc_repo, actor_repo, target_id, target_type)
    scene = await _fetch_scene(scene_id, config)

    query = f"{reason} {plot_brief} {scene.get('description', '')}".strip()
    memories = await retrieve_memories(char_id, query, config=config, top_k=5)

    ctx = {
        "initiator": _character_ctx(char_id, initiator),
        "target": _character_ctx(target_id, target),
        "reason": reason,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memories,
        "scene": scene,
    }
    try:
        system = _PROMPTS.get_template("talk/_dialogue_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("talk/dialogue.jinja").render(**ctx)
    except Exception:
        logger.exception("[engine] dialogue prompt render failed")
        return []

    try:
        result = await llm.call_structured(
            "talk",
            DialogueSchema,
            [
                SystemMessage(content=system),
                HumanMessage(content=prompt),
            ],
            fallback=lambda: DialogueSchema(turns=[]),
        )
    except Exception:
        logger.exception("[engine] dialogue generation failed for %s -> %s", char_id, target_id)
        return []

    return [t.model_dump() for t in result.turns]


async def _fetch_scene(scene_id: str, config: RunnableConfig = None) -> dict:
    """按 scene_id 查询场景信息 / Fetch scene info by id."""
    scene_repo = get_repo(config, "scene")
    empty = {"id": scene_id, "name": "", "type": "", "description": ""}
    if not scene_repo or not scene_id:
        return empty
    scene = await scene_repo.get_scene(scene_id)
    return scene or empty


async def _load_target(pc_repo, actor_repo, target_id: str, target_type: str):
    """按 target_type 加载对话对象 / Load the dialogue target by its type."""
    if not target_id:
        return None
    if target_type == "pc":
        return await pc_repo.load_one(target_id) if pc_repo else None
    return await actor_repo.load_one(target_id) if actor_repo else None


def _character_ctx(char_id: str, char) -> dict:
    """组装角色 prompt 上下文 / Build character prompt context."""
    if not char:
        return {"id": char_id, "name": char_id, "role": "", "personality": ""}
    return {
        "id": char.id,
        "name": char.name,
        "role": getattr(char, "role", ""),
        "personality": getattr(char, "personality", ""),
    }


def _normalize_speaker_ids(turns: list[dict], char_id: str, target_id: str) -> list[dict]:
    """把 LLM 返回的 speaker_id 映射为真实角色 id / Map LLM speaker_ids to real character ids."""
    if not turns:
        return turns
    distinct = []
    seen = set()
    for t in turns:
        sid = t.get("speaker_id", "")
        if sid and sid not in seen:
            seen.add(sid)
            distinct.append(sid)

    # 如果所有 speaker_id 已经是真实 id，无需映射
    # If all speaker_ids are already real ids, skip mapping
    valid = {char_id, target_id}
    if all(sid in valid for sid in distinct):
        return turns

    mapping: dict[str, str] = {}
    if distinct:
        mapping[distinct[0]] = char_id
    if len(distinct) > 1:
        mapping[distinct[1]] = target_id

    return [
        {**t, "speaker_id": mapping.get(t.get("speaker_id", ""), t.get("speaker_id", ""))}
        for t in turns
    ]


async def _store_dialogue_memory(
    char_id: str,
    target_id: str,
    turns: list[dict],
    tick: int,
    config: RunnableConfig = None,
) -> None:
    """把对话记录存入双方记忆，供后续决策/反思检索 / Store the exchange into both participants' memory."""
    memory_repo = get_repo(config, "memory")
    if not memory_repo:
        return
    transcript = "；".join(f"{t['speaker_id']}：{t['text']}" for t in turns)
    if char_id:
        await memory_repo.store(char_id, f"与 {target_id} 的对话：{transcript}", tick, importance=3)
    if target_id:
        await memory_repo.store(target_id, f"与 {char_id} 的对话：{transcript}", tick, importance=3)


def _update_talker_position(
    pc_id: str,
    target_id: str,
    target_type: str,
    pc_state_map: dict[str, dict] | None,
    actor_state_map: dict[str, dict] | None = None,
) -> list[dict]:
    """谈话者移到目标旁边空位，返回 waypoints / Move talker to vacant adjacent cell"""
    if not pc_state_map or pc_id not in pc_state_map:
        return []
    target_map = pc_state_map if target_type == "pc" else actor_state_map
    target = (target_map or {}).get(target_id, {})
    tx, ty = target.get("position_x", 0), target.get("position_y", 0)
    if tx == 0 and ty == 0:
        return []
    old_x = pc_state_map[pc_id].get("position_x", 0)
    old_y = pc_state_map[pc_id].get("position_y", 0)

    from ...utils.helpers import build_occupied_set, find_vacant_adjacent

    occupied = build_occupied_set(pc_state_map, actor_state_map, exclude_id=pc_id)
    new_x, new_y = find_vacant_adjacent(tx, ty, occupied)

    pc_state_map[pc_id]["position_x"] = new_x
    pc_state_map[pc_id]["position_y"] = new_y
    if old_x == new_x and old_y == new_y:
        return []
    return [{"x": old_x, "y": old_y}, {"x": new_x, "y": new_y}]
