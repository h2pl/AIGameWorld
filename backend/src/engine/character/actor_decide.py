"""Actor Decide Engine——LLM 驱动的浅层决策 / Actor shallow decision with LLM."""
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import CharacterActionSchema
from ...schemas.request import ActorDecideRequest
from ...schemas.response import ActorDecideResponse

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
_VALID_ACTIONS = {"move", "talk", "attack", "interact", "wait"}


def _get_repos(config: RunnableConfig | None):
    if config and "configurable" in config:
        return config["configurable"].get("repos")
    return None


async def actor_decide(req: ActorDecideRequest, config: RunnableConfig = None) -> ActorDecideResponse:
    _cfg = config.get("configurable", {}) if config else {}
    llm = _cfg.get("llm")
    if llm is None:
        return _fallback(req)
    try:
        repos = _get_repos(config)
        char_repo = repos.get("char") if repos else None
        memory_repo = repos.get("memory") if repos else None

        actor = await char_repo.load_actor(req.actor_id) if char_repo else None
        query = req.plot_brief or "最近发生了什么"
        memories = await memory_repo.retrieve(req.actor_id, query, top_k=3) if memory_repo else []
        ctx = {
            "name": actor.name if actor else req.actor_id, "character_type": "actor",
            "role": actor.role if actor else "",
            "personality": actor.personality if actor else "",
            "functions": actor.functions if actor else [],
            "plot_brief": req.plot_brief, "equipment": {},
            "memories": [{"content": m.content} for m in memories],
        }

        system = _PROMPTS.get_template("_character_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("character/actor_decide.jinja").render(**ctx)
        result = await llm.call_structured(
            "actor_decision", CharacterActionSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: CharacterActionSchema(action_type="wait", reasoning="LLM 降级。"),
        )

        result = _validate(result)
        return ActorDecideResponse(character_id=req.actor_id, type=result.action_type, description=result.reasoning)
    except Exception:
        logger.exception("actor_decide LLM failed for %s", req.actor_id)
        return _fallback(req)


def _validate(result: CharacterActionSchema) -> CharacterActionSchema:
    if result.action_type not in _VALID_ACTIONS:
        result.action_type = "wait"
    if not result.reasoning or not result.reasoning.strip():
        result.reasoning = "继续日常行为。"
    return result


def _fallback(req: ActorDecideRequest) -> ActorDecideResponse:
    return ActorDecideResponse(character_id=req.actor_id, type="idle", description=f"{req.actor_id} goes about their business.")
