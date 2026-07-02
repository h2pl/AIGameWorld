"""Character Decision Engine——加载角色并逐个决策."""

import logging

from langchain_core.runnables.config import RunnableConfig

from ....schemas.request import ActorDecideRequest, PCDecideRequest
from . import actor_decide, pc_decide

logger = logging.getLogger("aw.eng.char")


async def process_characters(
    contexts: list[dict],
    tick: int,
    config: RunnableConfig = None,
) -> list[dict]:
    """基于每个角色的感知上下文逐个决策 / Decide per perceived character context."""
    logger.info("[character] tick=%s processing %d characters", tick, len(contexts))

    actions: list[dict] = []
    for ctx in contexts:
        char_type = ctx.get("character_type", "actor")
        char_id = ctx.get("character_id", "")
        plot_brief = ctx.get("plot_brief", "")
        try:
            if char_type == "pc":
                result = await pc_decide.pc_decide(
                    PCDecideRequest(pc_id=char_id, plot_brief=plot_brief, tick=tick), config
                )
            else:
                result = await actor_decide.actor_decide(
                    ActorDecideRequest(actor_id=char_id, plot_brief=plot_brief, tick=tick), config
                )
            if result:
                actions.append(result.model_dump())
        except Exception:
            logger.exception("[character] failed for %s %s", char_type, char_id)

    return actions
