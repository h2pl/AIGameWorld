"""编排器 / Orchestrator: 主图入口 + run_tick() 控制 / Main graph entry + tick control.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from ..graph.checkpoints import create_dev_checkpointer
from ..graph.graph import build_tick_graph, OverallState


class Orchestrator:
    """TickGraph 编排器 / Orchestrates the TickGraph.

    职责 / Responsibilities:
    - 初始化 TickGraph + Checkpointer / Initialize graph + checkpointer
    - 管理 tick 执行 / Manage tick execution
    - 对外提供 run_tick() 接口 / Public run_tick() interface
    """

    def __init__(
        self,
        session_id: str = "default",
        checkpointer: BaseCheckpointSaver | None = None,
        dm_agent: Any = None,  # Optional[DMAgent] for Phase 2+ LLM
        reflection_interval: int = 5,
    ):
        # 构建主图 / Build main graph
        self._graph = build_tick_graph()
        # Checkpointer：可注入，默认开发环境内存版 / Injectable, defaults to dev in-memory
        self._checkpointer = checkpointer or create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        # 当前 tick 号 / Current tick number
        self._tick = 0
        # Graph 配置：按 session_id 隔离存档 / Config isolated by session_id
        self._config = {"configurable": {"thread_id": session_id}}
        # Phase 2+ DMAgent 注入 / DMAgent for Phase 2+ LLM
        self._dm_agent = dm_agent
        self._reflection_interval = reflection_interval

    @property
    def tick(self) -> int:
        """当前 tick 号 / Current tick number."""
        return self._tick

    async def run_tick(self, initial_state: OverallState | None = None) -> dict:
        """执行一个完整 Tick（7 Phase）/ Execute one complete tick.

        Args:
            initial_state: 初始状态（首次从 WorldState 构造）

        Returns:
            dict: 包含 narrative 和 events 的结果
        """
        if initial_state is None:
            initial_state = OverallState(
                tick=self._tick,
                dm_instructions=[],
                plot_brief="",
                scene_direction={},
                world_events=[],
                character_actions=[],
                engine_results=[],
                combat_result=None,
                state_diff={},
                cast_changes=[],
                narrative="",
                reflected_characters=[],
                summary_compressed=False,
                errors=[],
                needs_reflection=False,
            )

        initial_state["tick"] = self._tick

        # Phase 2+: 如有 DMAgent，通过 config 传递给 graph nodes
        config = {**self._config}
        if self._dm_agent:
            config["configurable"]["dm_agent"] = self._dm_agent
            config["configurable"]["reflection_interval"] = self._reflection_interval

        result = await self._app.ainvoke(initial_state, config)

        self._tick += 1

        return {
            "tick": result["tick"],
            "narrative": result.get("narrative", ""),
            "events": result.get("world_events", []),
            "character_actions": result.get("character_actions", []),
            "errors": result.get("errors", []),
        }

    def get_state(self) -> OverallState:
        """获取当前会话的最新状态 / Get latest state for current session."""
        return self._app.get_state(self._config)

    def get_history(self) -> list[OverallState]:
        """获取当前会话的执行历史（支持时间旅行）/ Get execution history for time travel."""
        return list(self._app.get_state_history(self._config))

    def rollback(self, tick: int) -> OverallState:
        """回滚到指定 tick 的状态 / Rollback state to a specific tick."""
        for state in self.get_history():
            if state.metadata.get("tick") == tick:
                self._app.update_state(self._config, state.values)
                self._tick = tick
                return state.values
        raise ValueError(f"Tick {tick} not found in session history")

    def reset(self) -> None:
        """重置 tick 计数器 / Reset tick counter."""
        self._tick = 0
