"""Graph 生产者——根据配置选择 mock 或真实链路."""

import asyncio
import logging
from datetime import datetime, timezone

from ..config import load_config
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
    """选择并运行 producer / Select and run producer."""
    if load_config().mock_mode:
        from ..mock.producer import run as mock_run

        await mock_run(world_id, msg_repo, evt_repo, get_paused, db)
    else:
        await _real_run(world_id, msg_repo, evt_repo, get_paused, db)


async def _real_run(
    world_id: str,
    msg_repo: MessageRepo,
    evt_repo: EventRepo,
    get_paused: callable,
    db,
) -> None:
    """真实 Orchestrator 链路."""
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
                id=world_id, tick=result["tick"], world_id=world_id,
                timestamp=datetime.now(timezone.utc), events=events,
            )
            await msg_repo.insert(msg)
            await evt_repo.insert_batch(msg.id, msg.tick, msg.events)
            logger.info("[Graph] %s tick=%d events=%d", world_id, msg.tick, len(msg.events))
    except Exception as e:
        logger.error("[Graph] %s error: %s", world_id, e, exc_info=True)
