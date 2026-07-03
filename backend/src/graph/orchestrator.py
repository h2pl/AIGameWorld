"""编排器 / Orchestrator: 全局单例，管理多个 world 的 tick 执行."""

import time
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import StateSnapshot

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
        self._graph = build_tick_graph()
        self._checkpointer = checkpointer or checkpoints.create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        self._llm = llm
        self._reflection_interval = reflection_interval
        self._repos = repos

    async def run_tick(self, world_id: str) -> dict:
        """对指定 world 执行一个完整 Tick——tick 号从 worlds 表读取并自增."""
        world_repo = self._repos.get("world") if self._repos else None
        tick = await world_repo.increment_tick(world_id) if world_repo else 1

        initial_state = OverallState(
            tick=tick,
            world_id=world_id,
            tick_message_id="",
            scene_info={},
            pending_actions=[],
            hints=[],
            plot_brief="",
            scene_id="",
            pc_decisions=[],
            narrative="",
        )
        if tick > 1:
            prev = self._app.get_state({"configurable": {"thread_id": world_id}})
            if prev and prev.values:
                initial_state["plot_brief"] = prev.values.get("plot_brief", "")

        config = self._make_config(world_id)
        config["callbacks"] = [TickGraphCallback(tick=tick)]

        t_start = time.monotonic()
        result = await self._app.ainvoke(initial_state, config)
        log_phase("tick", tick, elapsed=time.monotonic() - t_start)

        return {
            "tick": result["tick"],
            "tick_message_id": result.get("tick_message_id", ""),
            "narrative": result.get("narrative", ""),
            "pc_decisions": result.get("pc_decisions", []),
        }

    def _make_config(self, world_id: str) -> dict:
        config: dict[str, Any] = {"configurable": {"thread_id": world_id}}
        if self._llm:
            config["configurable"]["llm"] = self._llm
            config["configurable"]["reflection_interval"] = self._reflection_interval
        if self._repos:
            config["configurable"]["repos"] = self._repos
        return config

    def get_state(self, world_id: str) -> StateSnapshot:
        return self._app.get_state({"configurable": {"thread_id": world_id}})

    def get_history(self, world_id: str) -> list[StateSnapshot]:
        return list(self._app.get_state_history({"configurable": {"thread_id": world_id}}))

    async def reset(self, world_id: str) -> None:
        """重置 world tick 为 0."""
        world_repo = self._repos.get("world") if self._repos else None
        if world_repo:
            await world_repo.reset_tick(world_id)
