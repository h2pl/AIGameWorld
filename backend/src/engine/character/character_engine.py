"""Character Process Engine——加载角色 → 逐个决策.

只做决策，不写事件 / Decision only, no event writing.
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...schemas.request import ActorDecideRequest, PCDecideRequest
from ...utils.helpers import get_repo
from .actor_decide import actor_decide as _actor_decide
from .pc_decide import pc_decide as _pc_decide

logger = logging.getLogger("aw.eng.char")


async def process_characters(
    world_id: str,
    tick: int,
    plot_brief: str,
    config: RunnableConfig = None,
) -> list[dict]:
    """加载全部角色 → 逐个 LLM 决策 → 返回 action 列表."""
    char_repo = get_repo(config, "char")
    if not char_repo:
        logger.warning("[character] no char_repo, skip")
        return []

    pcs = await char_repo.load_pcs(world_id) if world_id else []
    actors = await char_repo.load_actors(world_id) if world_id else []
    all_chars = [("pc", pc.id) for pc in pcs] + [("actor", a.id) for a in actors]
    logger.info("[character] tick=%s processing %d characters", tick, len(all_chars))

    actions: list[dict] = []
    for char_type, char_id in all_chars:
        try:
            if char_type == "pc":
                result = await _pc_decide(
                    PCDecideRequest(pc_id=char_id, plot_brief=plot_brief, tick=tick), config
                )
            else:
                result = await _actor_decide(
                    ActorDecideRequest(actor_id=char_id, plot_brief=plot_brief, tick=tick), config
                )
            if result:
                actions.append(result.model_dump())
        except Exception:
            logger.exception("[character] failed for %s %s", char_type, char_id)

    return actions
