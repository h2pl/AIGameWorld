"""Talk Engine——处理角色交谈动作 / Handle character talk actions.

单次 LLM 调用生成双方多轮对话（turns 数组），返回 character_talk 事件供上层收集后统一落盘，
并把对话存入双方记忆。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import DialogueSchema
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
    config: RunnableConfig = None,
) -> dict | None:
    """处理单个 talk 决策 → 生成多轮对话，返回原始对话结果（不构造事件）/
    Resolve a single talk decision, return the raw dialogue result (not an event)."""
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
        # 降级：没有 LLM/目标时只保留发起者一句话 / fallback: initiator-only line
        turns = [{"speaker_id": char_id, "text": reason or f"{char_id} 发起交谈。"}]

    _store_dialogue_memory(char_id, target_id, turns, tick, config)

    logger.info("[engine] %s ↔ %s : %d turns", char_id, target_id, len(turns))
    return {
        "kind": "pc_talk",
        "participants": [pid for pid in (char_id, target_id) if pid],
        "turns": turns,
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
    initiator = await pc_repo.load_pc(char_id) if pc_repo else None
    target = await _load_target(pc_repo, target_id, target_type)
    scene = await _fetch_scene(scene_id, config)

    ctx = {
        "initiator": _character_ctx(char_id, initiator),
        "target": _character_ctx(target_id, target),
        "reason": reason,
        "plot_brief": plot_brief,
        "hints": hints,
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
            "dialogue",
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


async def _load_target(pc_repo, target_id: str, target_type: str):
    """按 target_type 加载对话对象 / Load the dialogue target by its type."""
    if not pc_repo or not target_id:
        return None
    if target_type == "pc":
        return await pc_repo.load_pc(target_id)
    return await pc_repo.load_actor(target_id)


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


def _store_dialogue_memory(
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
        memory_repo.store(char_id, f"与 {target_id} 的对话：{transcript}", tick, importance=3)
    if target_id:
        memory_repo.store(target_id, f"与 {char_id} 的对话：{transcript}", tick, importance=3)
