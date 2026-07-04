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
        self._fallback_ticks: dict[str, int] = {}

    async def run_tick(self, world_id: str) -> dict:
        """对指定 world 执行一个完整 Tick——data_tick 从 worlds 表读取并自增."""
        world_repo = self._repos.get("world") if self._repos else None
        if world_repo:
            tick = await world_repo.increment_data_tick(world_id)
        else:
            t = self._fallback_ticks.get(world_id, 0) + 1
            self._fallback_ticks[world_id] = t
            tick = t

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
        result: dict[str, Any] | Any = await self._app.ainvoke(initial_state, config)
        log_phase("tick", tick, elapsed=time.monotonic() - t_start)

        return {
            "tick": result["tick"],
            "tick_message_id": result.get("tick_message_id", ""),
            "narrative": result.get("narrative", ""),
            "pc_decisions": result.get("pc_decisions", []),
        }

    def _make_config(self, world_id: str) -> dict:
        """构造 LangGraph 执行配置 / Build LangGraph run config."""
        config: dict[str, Any] = {"configurable": {"thread_id": world_id}}
        # 注入 LLM 与反思间隔 / Inject LLM and reflection interval
        if self._llm:
            config["configurable"]["llm"] = self._llm
            config["configurable"]["reflection_interval"] = self._reflection_interval
        # 注入仓库集合 / Inject repository collection
        if self._repos:
            config["configurable"]["repos"] = self._repos
        return config

    def get_state(self, world_id: str) -> StateSnapshot:
        """获取指定 world 的当前图状态 / Get current graph state for world."""
        return self._app.get_state({"configurable": {"thread_id": world_id}})

    def get_history(self, world_id: str) -> list[StateSnapshot]:
        """获取指定 world 的状态历史 / Get graph state history for world."""
        return list(self._app.get_state_history({"configurable": {"thread_id": world_id}}))

    async def reset(self, world_id: str) -> None:
        """重置 world data_tick 和 display_tick 为 0 / Reset world ticks to 0."""
        world_repo = self._repos.get("world") if self._repos else None
        if world_repo:
            await world_repo.reset_tick(world_id)
        else:
            self._fallback_ticks[world_id] = 0

    def rollback(self, world_id: str, tick: int) -> dict:
        """回滚到指定 tick 的状态 / Rollback world to specified tick."""
        for state in self.get_history(world_id):
            if state.metadata.get("tick") == tick:
                # 用历史状态更新当前状态 / Update current state with historical values
                self._app.update_state({"configurable": {"thread_id": world_id}}, state.values)
                self._fallback_ticks[world_id] = tick
                return state.values
        raise ValueError(f"Tick {tick} not found in {world_id}")
