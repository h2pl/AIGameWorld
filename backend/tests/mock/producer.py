"""Mock Graph 生产者——不依赖真实 LLM，用 MockTickEngine 生成 tick."""

import asyncio
import logging
from datetime import datetime

from src.domain.event import CharacterMoveEvent, DmNarrativeEvent, OpeningEvent
from src.domain.message import Message
from src.repository.event_repo import EventRepo
from src.repository.message_repo import MessageRepo
from tests.mock.tick_engine import MockTickEngine

logger = logging.getLogger("aw.producer")


async def run(
    world_id: str,
    msg_repo: MessageRepo,
    evt_repo: EventRepo,
    get_paused: callable,
    db,
) -> None:
    """循环产 tick → 写两表，带反压."""
    engine = MockTickEngine()
    # 开场白 / Opening
    msg = Message(
        id=world_id,
        tick=0,
        world_id=world_id,
        timestamp=datetime.now(datetime.timezone.utc),
        events=[OpeningEvent(text="冒险开始了！")],
    )
    await msg_repo.insert(msg)
    await evt_repo.insert_batch(msg.id, msg.tick, msg.events)

    try:
        while True:
            while get_paused():
                await asyncio.sleep(0.5)

            # 反压 / Backpressure
            backlog = await db.fetch_one(
                "SELECT COUNT(*) as cnt FROM messages WHERE id=? AND status='pending'",
                (world_id,),
            )
            if backlog and backlog.get("cnt", 0) > 5:
                await asyncio.sleep(0.3)
                continue

            data = engine.generate_tick()
            events = [DmNarrativeEvent(text=data.get("narrative", ""))]
            events.extend(
                CharacterMoveEvent(character_id=m["character_id"], x=m["x"], y=m["y"])
                for m in data.get("character_moves", [])
            )
            msg = Message(
                id=world_id,
                tick=data["tick"],
                world_id=world_id,
                timestamp=datetime.now(datetime.timezone.utc),
                events=events,
            )
            await msg_repo.insert(msg)
            await evt_repo.insert_batch(msg.id, msg.tick, msg.events)
            logger.info("[Mock] %s tick=%d events=%d", world_id, msg.tick, len(msg.events))
    except Exception as e:
        logger.error("[Mock] %s error: %s", world_id, e, exc_info=True)
