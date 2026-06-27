"""CheckpointStore — LangGraph checkpoint 适配器 / LangGraph checkpoint adapter.

基于 docs/06-data-layer.md §9 / Based on docs/06-data-layer.md §9.

MVP 使用 MemorySaver（内存，重启丢）/ MVP uses MemorySaver (in-memory, lost on restart).
生产可换 SqliteSaver / Production can switch to SqliteSaver.
"""

from langgraph.checkpoint.memory import MemorySaver


class CheckpointStore:
    """每 Tick 存档点，支持回放与回滚 / Per-tick checkpoint, supports replay and rollback.
    
    用途 / Uses:
    - 单步调试 / Single-step debugging
    - 回退到某 Tick 重跑 / Rollback to any tick for replay
    - 崩溃恢复（配合 SQLite WorldState）/ Crash recovery (with SQLite WorldState)
    """

    def __init__(self) -> None:
        self.saver = MemorySaver()

    def get_config(self, thread_id: str, checkpoint_id: str) -> dict:
        """构建 LangGraph config dict / Build LangGraph config dict."""
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "checkpoint_ns": "",    # 命名空间（必填）/ Namespace (required)
            }
        }

    def put(self, thread_id: str, checkpoint_id: str, state: dict) -> None:
        """保存一个 checkpoint / Save a checkpoint."""
        config = self.get_config(thread_id, checkpoint_id)
        self.saver.put(config, state, metadata={"tick": checkpoint_id}, new_versions={})

    def get(self, thread_id: str, checkpoint_id: str) -> dict | None:
        """读取指定 checkpoint / Get a specific checkpoint."""
        config = self.get_config(thread_id, checkpoint_id)
        return self.saver.get(config)

    def latest(self, thread_id: str) -> dict | None:
        """恢复到最新存档点 / Restore to latest checkpoint."""
        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        return self.saver.get(config)
