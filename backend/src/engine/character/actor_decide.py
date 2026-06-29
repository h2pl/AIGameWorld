"""Actor Decide Engine——LLM 驱动的浅层决策 / Actor shallow decision with LLM."""

# ── 依赖 / Dependencies ──
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import CharacterActionSchema
from ...schemas.request import ActorDecideRequest
from ...schemas.response import ActorDecideResponse
from ...utils.helpers import get_llm, get_repo

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
_VALID_ACTIONS = {"move", "talk", "attack", "interact", "wait"}

# ── 主决策入口 / Main decision entry ──


async def actor_decide(
    req: ActorDecideRequest, config: RunnableConfig = None
) -> ActorDecideResponse:
    llm = get_llm(config)
    if llm is None:
        return ActorDecideResponse(
            character_id=req.actor_id,
            type="idle",
            description=f"{req.actor_id} goes about their business.",
            errors=["LLM 不可用，使用降级输出 / LLM unavailable, fallback used"],
        )
    try:
        char_repo = get_repo(config, "char")
        memory_repo = get_repo(config, "memory")

        actor = await char_repo.load_actor(req.actor_id) if char_repo else None
        query = req.plot_brief or "最近发生了什么"
        memories = memory_repo.retrieve(req.actor_id, query, top_k=3) if memory_repo else []
        ctx = {
            "name": actor.name if actor else req.actor_id,
            "character_type": "actor",
            "role": actor.role if actor else "",
            "personality": actor.personality if actor else "",
            "functions": actor.functions if actor else [],
            "plot_brief": req.plot_brief,
            "equipment": {},
            "memories": [{"content": m.content} for m in memories],
        }

        system = _PROMPTS.get_template("_character_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("character/actor_decide.jinja").render(**ctx)
        result = await llm.call_structured(
            "actor_decision",
            CharacterActionSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: CharacterActionSchema(action_type="wait", reasoning="LLM 降级。"),
        )

        result = _validate(result)
        return ActorDecideResponse(
            character_id=req.actor_id, type=result.action_type, description=result.reasoning
        )
    except Exception:
        logger.exception("actor_decide LLM failed for %s", req.actor_id)
        return ActorDecideResponse(
            character_id=req.actor_id,
            type="idle",
            description=f"{req.actor_id} goes about their business.",
            errors=["actor_decide LLM 调用失败，使用降级输出"],
        )


# ── 护栏 + 降级 / Guardrails + fallback ──


def _validate(result: CharacterActionSchema) -> CharacterActionSchema:
    if result.action_type not in _VALID_ACTIONS:
        result.action_type = "wait"
    if not result.reasoning or not result.reasoning.strip():
        result.reasoning = "继续日常行为。"
    return result
