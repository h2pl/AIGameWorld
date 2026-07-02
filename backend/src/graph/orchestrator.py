"""编排器 / Orchestrator: 主图入口 + run_tick() 控制."""

import time
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import StateSnapshot

from ..utils.logging import log_phase
from . import checkpoints
from .graph import OverallState, build_tick_graph


class Orchestrator:
    """TickGraph 编排器 / TickGraph orchestrator."""

    def __init__(
        self,
        session_id: str = "default",
        checkpointer: BaseCheckpointSaver | None = None,
        llm: Any = None,
        reflection_interval: int = 5,
        repos: Any = None,
    ):
        self._graph = build_tick_graph()
        self._checkpointer = checkpointer or checkpoints.create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        self._tick = 1
        self._config = {"configurable": {"thread_id": session_id}}
        self._llm = llm
        self._reflection_interval = reflection_interval
        self._repos = repos

    @property
    def tick(self) -> int:
        return self._tick

    async def run_tick(self, initial_state: OverallState | None = None) -> dict:
        """执行一个完整 Tick（7 Phase） / Run one complete tick (7 phases)."""
        if initial_state is None:
            initial_state = OverallState(
                tick=self._tick,
                world_id="",
                tick_message_id="",
                scene_info={},
                pending_events=[],
                hints=[],
                plot_brief="",
                scene_id="",
                character_decisions=[],
                narrative="",
                reflected_characters=[],
                summary_compressed=False,
                errors=[],
                needs_reflection=False,
            )
            # P2-5: 非首轮从 checkpoint 恢复 plot_brief，保证 DM 剧情跨 tick 连续 /
            #       non-first tick: restore plot_brief from checkpoint for continuity
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

        t_start = time.monotonic()
        result = await self._app.ainvoke(initial_state, config)
        log_phase(
            "tick",
            self._tick,
            elapsed=time.monotonic() - t_start,
            errors=len(result.get("errors", [])),
        )
        self._tick += 1

        return {
            "tick": result["tick"],
            "narrative": result.get("narrative", ""),
            "character_decisions": result.get("character_decisions", []),
            "errors": result.get("errors", []),
        }

    def get_state(self) -> StateSnapshot:
        """返回当前 tick 的 checkpoint 快照 / Return current tick checkpoint snapshot."""
        return self._app.get_state(self._config)

    def get_history(self) -> list[StateSnapshot]:
        """返回所有历史 checkpoint 快照 / Return all historical checkpoint snapshots."""
        return list(self._app.get_state_history(self._config))

    def rollback(self, tick: int) -> dict:
        for state in self.get_history():
            if state.metadata.get("tick") == tick:
                self._app.update_state(self._config, state.values)
                self._tick = tick
                return state.values
        raise ValueError(f"Tick {tick} not found in session history")

    def reset(self) -> None:
        self._tick = 1
