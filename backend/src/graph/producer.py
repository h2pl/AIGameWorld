"""真实 Graph 生产者——用 Orchestrator 跑 tick / Real Graph producer using Orchestrator."""

import asyncio
import logging
from datetime import datetime, timezone

from ..domain.event import DmNarrativeEvent
from ..domain.message import Message
from ..repository.event_repo import EventRepo
from ..repository.message_repo import MessageRepo

logger = logging.getLogger("aw.producer")


async def run(
    world_id: str,
    msg_repo: MessageRepo,
    evt_repo: EventRepo,
    get_paused: callable,
    db,
) -> None:
    """用真实 Orchestrator 跑 tick 循环."""
    from ..graph.orchestrator import Orchestrator
    from ..repository.character_repo import CharacterRepo
    from ..repository.story_repo import StoryRepo

    char_repo = CharacterRepo(db)
    story_repo = StoryRepo(db)
    orch = Orchestrator(session_id=world_id, repos={"char": char_repo, "story": story_repo})

    try:
        while True:
            while get_paused():
                await asyncio.sleep(0.5)
            result = await orch.run_tick()
            events = [DmNarrativeEvent(text=result.get("narrative", ""))]
            events.extend(
                DmNarrativeEvent(text=f"{a.get('character_id', '?')}: {a.get('description', '')}")
                for a in result.get("character_actions", [])
            )
            msg = Message(
                id=world_id,
                tick=result["tick"],
                world_id=world_id,
                timestamp=datetime.now(timezone.utc),
                events=events,
            )
            await msg_repo.insert(msg)
            await evt_repo.insert_batch(msg.id, msg.tick, msg.events)
            logger.info("[Graph] %s tick=%d events=%d", world_id, msg.tick, len(msg.events))
    except Exception as e:
        logger.error("[Graph] %s error: %s", world_id, e, exc_info=True)
