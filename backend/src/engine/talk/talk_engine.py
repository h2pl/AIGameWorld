"""Talk Engine——处理角色交谈动作 / Handle character talk actions.

单次 LLM 调用生成双方多轮对话（turns 数组），返回 character_talk 事件供上层收集后统一落盘，
并把对话存入双方记忆。
"""

from pathlib import Path
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from src.utils.tracing import traced

from ...domain import (
    Action,
    Actor,
    Decision,
    DMRecord,
    Memory,
    MemoryType,
    PlayerCharacter,
    Scene,
    SceneObject,
    importance_of,
)
from ...schemas.llm_output import DialogueSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


@traced()
async def process_talk_action(
    decision: Decision,
    tick: int,
    scene: Scene | None = None,
    scene_objects: list[SceneObject] | None = None,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
    dm_record: DMRecord | None = None,
    memories: dict[str, list[Memory]] | None = None,
    config: RunnableConfig = None,
) -> Action | None:
    """处理单个 talk 决策 → 生成多轮对话，更新发起者坐标到目标旁边，写入 memories"""
    if decision.type != "talk":
        return None

    char_id = decision.pc_id
    target_id = decision.target_id or ""
    target_type = decision.target_type or ""
    reason = decision.description
    plot_brief = dm_record.plot_brief if dm_record else ""
    hints = dm_record.hints if dm_record else []

    turns = await _generate_dialogue(
        char_id,
        target_id,
        target_type,
        reason,
        plot_brief,
        hints,
        scene,
        tick,
        memories,
        config,
    )
    if not turns:
        turns = [{"speaker_id": char_id, "text": reason or f"{char_id} 发起交谈。"}]
    else:
        turns = _normalize_speaker_ids(turns, char_id, target_id)

    # PC 记对话记忆，Actor 不记 / Only PC stores dialogue memory, actors don't
    if target_type != "actor":
        _store_dialogue_memory(char_id, target_id, target_type, turns, tick, memories)
    else:
        _store_dialogue_memory(char_id, None, target_type, turns, tick, memories)

    waypoints = _update_talker_position(
        char_id, target_id, target_type, pcs, actors, scene, scene_objects
    )

    # ==== 写入 GraphRAG 关系图谱 ====
    if target_id:
        neo4j_repo = get_repo(config, "neo4j")
        if neo4j_repo:
            await neo4j_repo.merge_relationship(
                start_label="Actor",
                start_key="id",
                start_val=char_id,
                end_label="Actor",
                end_key="id",
                end_val=target_id,
                rel_type="TALKED_TO",
                tick=tick,
            )

    logger.info("[engine] %s ↔ %s : %d turns", char_id, target_id, len(turns))
    return Action(
        pc_id=char_id,
        action_type="talk",
        target_id=target_id,
        target_type=target_type,
        participants=[pid for pid in (char_id, target_id) if pid],
        turns=turns,
        waypoints=waypoints,
    )


async def _generate_dialogue(
    char_id: str,
    target_id: str,
    target_type: str,
    reason: str,
    plot_brief: str,
    hints: list[str],
    scene: Scene | None,
    tick: int,
    memories: dict[str, list[Memory]] | None,
    config: RunnableConfig = None,
) -> list[dict]:
    """单次 LLM 调用生成双方多轮对话 / Generate a multi-turn dialogue in a single LLM call."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[talk] LLM client not configured")
    if not target_id:
        return []

    pc_repo = get_repo(config, "char")
    actor_repo = get_repo(config, "actor")
    initiator = await pc_repo.load_one(char_id) if pc_repo else None
    target = await _load_target(pc_repo, actor_repo, target_id, target_type)

    query = f"{scene.name if scene else ''} 与 {target.name if target else target_id} 对话".strip()
    # 反思检索用叙事性情境描述 / Narrative query for reflection retrieval
    char_name = initiator.name if initiator else char_id
    target_name = target.name if target else target_id
    reflection_query = (
        f"{char_name}在{scene.name if scene else '未知场景'}，与{target_name}相遇交谈"
    )
    if plot_brief:
        reflection_query += f"，{plot_brief}"
    memory_texts = await retrieve_memories(
        char_id,
        query,
        config=config,
        top_k=5,
        current_tick=tick,
        reflection_query=reflection_query,
    )

    # 注入关系记忆 / Inject relationship context
    neo4j_repo = get_repo(config, "neo4j")
    if neo4j_repo:
        rel_ctx = await neo4j_repo.get_semantic_context(char_id, scene.id if scene else None)
        if rel_ctx:
            memory_texts.insert(0, f"[关系网络]:\n{rel_ctx}")

    ctx = {
        "initiator": _character_ctx(char_id, initiator),
        "target": _character_ctx(target_id, target),
        "reason": reason,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memory_texts,
        "scene": scene,
    }
    try:
        system = _PROMPTS.get_template("talk/_dialogue_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("talk/dialogue.jinja").render(**ctx)
    except Exception:
        logger.exception("[engine] dialogue prompt render failed")
        return []

    result = await llm.call_structured(
        "talk",
        DialogueSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )
    return [{"speaker_id": t.speaker_id, "text": t.text} for t in result.turns]


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


def _store_dialogue_memory(
    char_id: str,
    target_id: str | None,
    target_type: str,
    turns: list[dict],
    tick: int,
    memories: dict[str, list[Memory]] | None,
) -> None:
    """把对话记录写入 memories，供后续决策/反思检索 / Stage dialogue memory into state."""
    if memories is None:
        return
    transcript = "；".join(f"{t['speaker_id']}：{t['text']}" for t in turns)
    if char_id:
        memories.setdefault(char_id, []).append(
            Memory(
                id=f"mem_{char_id}_{tick}_{uuid4().hex[:6]}",
                pc_id=char_id,
                content=f"与 {target_id} 的对话：{transcript}",
                tick=tick,
                importance=importance_of(MemoryType.TALK.value),
                memory_type=MemoryType.TALK.value,
                entity_type="pc",
            )
        )
    if target_id:
        memories.setdefault(target_id, []).append(
            Memory(
                id=f"mem_{target_id}_{tick}_{uuid4().hex[:6]}",
                pc_id=target_id,
                content=f"与 {char_id} 的对话：{transcript}",
                tick=tick,
                importance=importance_of(MemoryType.TALK.value),
                memory_type=MemoryType.TALK.value,
                entity_type="pc" if target_type == "pc" else "actor",
            )
        )


def _update_talker_position(
    pc_id: str,
    target_id: str,
    target_type: str,
    pcs: dict[str, PlayerCharacter] | None,
    actors: dict[str, Actor] | None = None,
    scene: Scene | None = None,
    scene_objects: list[SceneObject] | None = None,
) -> list[dict]:
    """谈话者移到目标旁边空位，返回 waypoints / Move talker to vacant adjacent cell"""
    if not pcs or pc_id not in pcs:
        return []
    pc = pcs[pc_id]
    target = (pcs if target_type == "pc" else actors or {}).get(target_id)
    if target is None:
        return []
    tx, ty = target.position_x, target.position_y
    if tx == 0 and ty == 0:
        return []
    old_x, old_y = pc.position_x, pc.position_y

    from ...utils.helpers import dict_without, validate_position

    new_x, new_y = validate_position(tx, ty, dict_without(pcs, pc_id), actors, scene, scene_objects)

    pc.position_x = new_x
    pc.position_y = new_y
    if old_x == new_x and old_y == new_y:
        return []
    return [{"x": old_x, "y": old_y}, {"x": new_x, "y": new_y}]
