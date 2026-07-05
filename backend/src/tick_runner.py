"""Tick 执行管理器 / Tick execution managers.

持续循环和一次性批量任务的全局单例，供 api 层路由使用.
"""

import asyncio

from src.utils.logging import get_logger

logger = get_logger(__name__)


class TickLoopManager:
    """持续 Tick 循环管理器."""

    def __init__(self):
        self.running_worlds: dict[str, bool] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.loop_ids: dict[str, int] = {}

    async def _loop(self, world_id: str, orch, loop_id: int):
        logger.info(f"[loop] Started continuous tick loop for world {world_id} (id: {loop_id})")
        while self.running_worlds.get(world_id, False) and self.loop_ids.get(world_id) == loop_id:
            try:
                await orch.run_tick(world_id)
                await asyncio.sleep(0.5)  # Prevent CPU hogging
            except asyncio.CancelledError:
                logger.info(f"[loop] Tick loop for {world_id} was cancelled")
                break
            except Exception as e:
                logger.error(f"[loop] Error in tick loop for {world_id}: {e}")
                self.running_worlds[world_id] = False
                break
        logger.info(f"[loop] Stopped continuous tick loop for world {world_id} (id: {loop_id})")

    def start(self, world_id: str, orch):
        if self.running_worlds.get(world_id):
            return
        self.running_worlds[world_id] = True
        loop_id = self.loop_ids.get(world_id, 0) + 1
        self.loop_ids[world_id] = loop_id
        self.tasks[world_id] = asyncio.create_task(self._loop(world_id, orch, loop_id))

    def stop(self, world_id: str):
        self.running_worlds[world_id] = False
        # We don't cancel immediately to let the current tick finish gracefully
        # The loop_id check ensures old loops will exit even if start is called quickly


class TickBatchRunner:
    """一次性 N-tick 任务管理器."""

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._targets: dict[str, int] = {}
        self._completed: dict[str, int] = {}

    async def _run(self, world_id: str, orch, n: int):
        logger.info(f"[batch] Started {n} ticks for world {world_id}")
        completed = 0
        try:
            for _ in range(n):
                task = self._tasks.get(world_id)
                if task and task.cancelled():
                    break
                await orch.run_tick(world_id)
                completed += 1
        except asyncio.CancelledError:
            logger.info(f"[batch] Cancelled for world {world_id} after {completed} ticks")
        except Exception as e:
            logger.error(f"[batch] Error in world {world_id}: {e}")
        finally:
            self._completed[world_id] = completed
            self._tasks.pop(world_id, None)
            self._targets.pop(world_id, None)
            logger.info(f"[batch] Finished world {world_id}: {completed}/{n} ticks")

    def start(self, world_id: str, orch, n: int):
        """启动一次性 N-tick 任务（不阻塞，前端主动拉取）."""
        if n <= 0:
            raise ValueError("n must be positive")
        existing = self._tasks.get(world_id)
        if existing is not None and not existing.done():
            raise RuntimeError(f"Batch already running for {world_id}")
        self._targets[world_id] = n
        self._tasks[world_id] = asyncio.create_task(self._run(world_id, orch, n))

    def is_running(self, world_id: str) -> bool:
        task = self._tasks.get(world_id)
        return task is not None and not task.done()

    def get_target(self, world_id: str) -> int | None:
        return self._targets.get(world_id)

    def get_completed(self, world_id: str) -> int | None:
        return self._completed.get(world_id)


loop_manager = TickLoopManager()
batch_runner = TickBatchRunner()
