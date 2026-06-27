"""编排器 / Orchestrator: 主图入口 + run_tick() 控制 / Main graph entry + tick control.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

from langgraph.checkpoint.memory import MemorySaver

from .tick_graph import build_tick_graph, OverallState


class Orchestrator:
    """TickGraph 编排器 / Orchestrates the TickGraph.
    
    职责 / Responsibilities:
    - 初始化 TickGraph + Checkpointer / Initialize graph + checkpointer
    - 管理 tick 执行 / Manage tick execution
    - 对外提供 run_tick() 接口 / Public run_tick() interface
    """

    def __init__(self):
        # 构建主图 / Build main graph
        self._graph = build_tick_graph()
        # MemorySaver: 内存级 Checkpoint / In-memory checkpointer
        self._checkpointer = MemorySaver()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        # 当前 tick 号 / Current tick number
        self._tick = 0
        # Graph 配置（每个 tick 新 thread_id）/ Graph config (new thread per tick)
        self._config = {"configurable": {"thread_id": "simgameworld"}}

    @property
    def tick(self) -> int:
        """当前 tick 号 / Current tick number."""
        return self._tick

    async def run_tick(self, initial_state: OverallState | None = None) -> dict:
        """执行一个完整 Tick（7 Phase）/ Execute one complete tick.
        
        Args:
            initial_state: 初始状态（首次从 WorldState 构造）/ Initial state (from WorldState for first tick)
            
        Returns:
            dict: 包含 narrative 和 events 的结果 / Result with narrative and events
        """
        if initial_state is None:
            # 后续 tick 从上次状态继续 / Subsequent ticks continue from previous state
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

        # 确保 tick 号正确 / Ensure correct tick number
        initial_state["tick"] = self._tick

        # 执行主图 / Run the main graph
        result = await self._app.ainvoke(initial_state, self._config)

        # 更新内部 tick / Update internal tick
        self._tick += 1

        return {
            "tick": result["tick"],
            "narrative": result.get("narrative", ""),
            "events": result.get("world_events", []),
            "errors": result.get("errors", []),
        }

    def reset(self) -> None:
        """重置 tick 计数器 / Reset tick counter."""
        self._tick = 0
