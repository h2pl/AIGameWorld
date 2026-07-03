"""Mock Graph 生产者——不依赖真实 LLM，用 MockTickEngine 生成 tick."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from src.domain.event import Event
from src.domain.message import Message
from src.repository.event_repo import TickEventRepo
from src.repository.message_repo import TickMessageRepo
from tests.mock.tick_engine import MockTickEngine

logger = logging.getLogger("aw.producer")


async def run(
    world_id: str,
    msg_repo: TickMessageRepo,
    evt_repo: TickEventRepo,
    get_paused: Callable[[], bool],
    db,
) -> None:
    """循环产 tick → 写两表，带反压."""
    engine = MockTickEngine()
    # 开场白 / Opening
    msg = Message(
        id=world_id,
        tick=0,
        world_id=world_id,
        timestamp=datetime.now(UTC).isoformat(),
    )
    await msg_repo.insert(msg)
    opening_evt = Event(type="opening", tick=0, payload={"text": "冒险开始了！"})
    await evt_repo.insert_events(msg.id, msg.tick, [opening_evt])
    await msg_repo.mark_ready(msg.id, msg.tick)

    try:
        while True:
            while get_paused():
                await asyncio.sleep(0.5)

            # 反压 / Backpressure
            backlog = await db.fetch_one(
                "SELECT COUNT(*) as cnt FROM tick_messages WHERE id=? AND status='pending'",
                (world_id,),
            )
            if backlog and backlog.get("cnt", 0) > 5:
                await asyncio.sleep(0.3)
                continue

            data = engine.generate_tick()
            tick = data["tick"]
            events: list[Event] = []
            if narrative := data.get("narrative", ""):
                events.append(Event(type="dm_narrative", tick=tick, payload={"text": narrative}))
            events.extend(
                Event(
                    type="character_move",
                    tick=tick,
                    payload={"character_id": m["character_id"], "x": m["x"], "y": m["y"]},
                )
                for m in data.get("character_moves", [])
            )
            msg = Message(
                id=world_id,
                tick=tick,
                world_id=world_id,
                timestamp=datetime.now(UTC).isoformat(),
            )
            await msg_repo.insert(msg)
            await evt_repo.insert_events(msg.id, msg.tick, events)
            await msg_repo.mark_ready(msg.id, msg.tick)
            logger.info("[Mock] %s tick=%d events=%d", world_id, msg.tick, len(events))
    except Exception:
        logger.error("[Mock] %s error", world_id, exc_info=True)
