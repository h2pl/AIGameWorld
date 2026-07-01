"""Talk Engine——角色交谈裁决 / Character talk resolution.

Phase 3: 角色 interaction，输出 character_talk 事件.
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...schemas.request import ActorDecideRequest, PCDecideRequest
from ...schemas.response import DialogueResponse
from ...utils.helpers import get_llm

logger = logging.getLogger("aw.eng")


async def talk_pc(req: PCDecideRequest, config: RunnableConfig = None) -> DialogueResponse | None:
    """PC 交谈裁决."""
    llm = get_llm(config)
    if llm is None:
        return None
    # TODO: 实现 PC 交谈逻辑，写入 character_talk 事件到 events 表
    return DialogueResponse(success=True, content="")


async def talk_actor(
    req: ActorDecideRequest, config: RunnableConfig = None
) -> DialogueResponse | None:
    """Actor 交谈裁决."""
    llm = get_llm(config)
    if llm is None:
        return None
    # TODO: 实现 Actor 交谈逻辑，写入 character_talk 事件到 events 表
    return DialogueResponse(success=True, content="")
