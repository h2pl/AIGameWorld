"""编排器 / Orchestrator: 全局单例，管理多个 world 的 tick 执行.

每个 tick 使用独立的 thread_id，避免累加器字段跨 tick 累积."""

import time
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from ..utils.graph_callbacks import TickGraphCallback
from ..utils.logging import get_logger, log_phase
from . import checkpoints
from .graph import OverallState, build_tick_graph

logger = get_logger(__name__)


class Orchestrator:
    """全局 TickGraph 编排器——一个实例处理所有 world."""

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        llm: Any = None,
        reflection_interval: int = 5,
        repos: Any = None,
    ):
        logger.info("[orchestrator] init")
        if repos is None:
            logger.error("[orchestrator] repos is required")
        self._graph = build_tick_graph()
        self._checkpointer = checkpointer or checkpoints.create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        self._llm = llm
        self._reflection_interval = reflection_interval
        self._repos = repos

    async def run_tick(self, world_id: str) -> dict:
        """对指定 world 执行一个完整 Tick——data_tick 从 worlds 表读取并自增."""
        world_repo = self._repos.get("world")
        if not world_repo:
            logger.error("[orchestrator] world repo not found")
            raise RuntimeError("world repo not found")

        tick = await world_repo.increment_data_tick(world_id)

        initial_state: OverallState = {"tick": tick, "world_id": world_id}

        config = self._make_config(world_id, tick)
        config["callbacks"] = [TickGraphCallback(tick=tick)]

        t_start = time.monotonic()
        result: dict[str, Any] | Any = await self._app.ainvoke(initial_state, config)
        log_phase("tick", tick, elapsed=time.monotonic() - t_start)

        return {"tick": result["tick"], "tick_message_id": result.get("tick_message_id", "")}

    def _make_config(self, world_id: str, tick: int) -> dict:
        """构造 LangGraph 执行配置 / Build LangGraph run config."""
        # 每个 tick 使用独立 thread_id，避免累加器字段跨 tick 累积
        config: dict[str, Any] = {
            "configurable": {
                "thread_id": f"{world_id}__tick_{tick}",
                "repos": self._repos,
            }
        }
        if self._llm:
            config["configurable"]["llm"] = self._llm
            config["configurable"]["reflection_interval"] = self._reflection_interval
        return config

    async def reset(self, world_id: str) -> None:
        """重置 world data_tick 和 display_tick 为 0 / Reset world ticks to 0."""
        world_repo = self._repos.get("world")
        if not world_repo:
            logger.error("[orchestrator] world repo not found")
            raise RuntimeError("world repo not found")
        await world_repo.reset_tick(world_id)
