"""编排器 / Orchestrator: 主图入口 + run_tick() 控制."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from ..graph import checkpoints
from ..graph.graph import build_tick_graph, OverallState


class Orchestrator:
    """TickGraph 编排器."""

    def __init__(
        self,
        session_id: str = "default",
        checkpointer: BaseCheckpointSaver | None = None,
        dm_llm: Any = None,
        reflection_interval: int = 5,
    ):
        self._graph = build_tick_graph()
        self._checkpointer = checkpointer or checkpoints.create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        self._tick = 0
        self._config = {"configurable": {"thread_id": session_id}}
        self._dm_llm = dm_llm
        self._reflection_interval = reflection_interval

    @property
    def tick(self) -> int:
        return self._tick

    async def run_tick(self, initial_state: OverallState | None = None) -> dict:
        """执行一个完整 Tick（7 Phase）."""
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

        config = {**self._config}
        if self._dm_llm:
            config["configurable"]["dm_llm"] = self._dm_llm
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
        return self._app.get_state(self._config)

    def get_history(self) -> list[OverallState]:
        return list(self._app.get_state_history(self._config))

    def rollback(self, tick: int) -> OverallState:
        for state in self.get_history():
            if state.metadata.get("tick") == tick:
                self._app.update_state(self._config, state.values)
                self._tick = tick
                return state.values
        raise ValueError(f"Tick {tick} not found in session history")

    def reset(self) -> None:
        self._tick = 0
