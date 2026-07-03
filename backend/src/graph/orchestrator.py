"""编排器 / Orchestrator: 主图入口 + run_tick() 控制，含全链路日志回调."""

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
    """TickGraph 编排器——含全链路日志回调."""

    def __init__(
        self,
        session_id: str = "default",
        checkpointer: BaseCheckpointSaver | None = None,
        llm: Any = None,
        reflection_interval: int = 5,
        repos: Any = None,
        debug: bool = False,
    ):
        logger.info("[orchestrator] init session=%s debug=%s", session_id, debug)
        self._graph = build_tick_graph()
        self._checkpointer = checkpointer or checkpoints.create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        self._tick = 1
        self._config = {"configurable": {"thread_id": session_id}}
        self._llm = llm
        self._reflection_interval = reflection_interval
        self._repos = repos
        self._debug = debug

    @property
    def tick(self) -> int:
        return self._tick

    async def run_tick(self, initial_state: OverallState | None = None) -> dict:
        """执行一个完整 Tick / Run one complete tick with full-chain callbacks.

        如果 self._debug=True，同时输出 astream_events 逐事件日志。
        If debug mode, also output astream_events verbosely.
        """
        if initial_state is None:
            initial_state = OverallState(
                tick=self._tick,
                world_id="",
                tick_message_id="",
                scene_info={},
                pending_actions=[],
                hints=[],
                plot_brief="",
                scene_id="",
                pc_decisions=[],
                narrative="",
            )
            # 非首轮从 checkpoint 恢复 / Restore from checkpoint for non-first ticks
            if self._tick > 1:
                prev = self._app.get_state(self._config)
                if prev and prev.values:
                    initial_state["plot_brief"] = prev.values.get("plot_brief", "")

        initial_state["tick"] = self._tick

        config = {**self._config}
        if self._llm:
            config["configurable"]["llm"] = self._llm
            config["configurable"]["reflection_interval"] = self._reflection_interval
        if self._repos:
            config["configurable"]["repos"] = self._repos

        # ── 全链路日志回调 / Full-chain logging callback ──
        callback = TickGraphCallback(tick=self._tick, debug=self._debug)
        config["callbacks"] = [callback]

        # ── 执行图 / Execute graph ──
        t_start = time.monotonic()
        if self._debug:
            # debug 模式：逐事件流式输出 / Debug mode: stream events one-by-one
            result: OverallState = initial_state
            async for event in self._app.astream_events(initial_state, config, version="v2"):
                _log_debug_event(event, self._tick)
                # 保持 state 追踪 / Keep track of state
                if event.get("event") == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        result = output
        else:
            result = await self._app.ainvoke(initial_state, config)

        log_phase("tick", self._tick, elapsed=time.monotonic() - t_start)
        self._tick += 1

        return {
            "tick": result["tick"],
            "narrative": result.get("narrative", ""),
            "pc_decisions": result.get("pc_decisions", []),
        }

    def get_state(self) -> StateSnapshot:
        """返回当前 tick 的 checkpoint 快照 / Return current tick checkpoint snapshot."""
        return self._app.get_state(self._config)

    def get_history(self) -> list[StateSnapshot]:
        """返回所有历史 checkpoint 快照 / Return all historical checkpoint snapshots."""
        return list(self._app.get_state_history(self._config))

    def rollback(self, tick: int) -> dict:
        """回滚到指定 tick / Rollback to specified tick."""
        for state in self.get_history():
            if state.metadata.get("tick") == tick:
                self._app.update_state(self._config, state.values)
                self._tick = tick
                return state.values
        raise ValueError(f"Tick {tick} not found in session history")

    def reset(self) -> None:
        """重置 tick 计数 / Reset tick counter."""
        self._tick = 1


# ═══════════════════════════════════════════════════════════════
# Debug 辅助 / Debug helpers
# ═══════════════════════════════════════════════════════════════


def _log_debug_event(event: dict[str, Any], tick: int) -> None:
    """输出 astream_events 中的关键事件 / Log key events from astream_events."""
    import logging

    logger = logging.getLogger("graph.debug")
    event_type = event.get("event", "")
    name = event.get("name", "")
    run_id = event.get("run_id", "")

    if event_type == "on_chain_start":
        logger.debug(f"[tick={tick}] ▶ {name} ({run_id})")
    elif event_type == "on_chain_end":
        logger.debug(f"[tick={tick}] ◀ {name} ({run_id})")
    elif event_type == "on_llm_start":
        logger.debug(f"[tick={tick}] 🤖 LLM start: {name} ({run_id})")
    elif event_type == "on_llm_end":
        logger.debug(f"[tick={tick}] ✅ LLM done: {name} ({run_id})")
    elif event_type == "on_chain_stream":
        chunk = event.get("data", {}).get("chunk", "")
        if chunk and hasattr(chunk, "content"):
            content = str(chunk.content)[:80]
            logger.debug(f"[tick={tick}] 📝 stream: {content}")
