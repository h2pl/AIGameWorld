"""CheckpointStore – LangGraph checkpoint adapter.

Based on docs/06-data-layer.md §9.
MVP uses MemorySaver; production can switch to SqliteSaver.
"""

from langgraph.checkpoint.memory import MemorySaver


class CheckpointStore:
    """Per-tick checkpoint store for LangGraph state graph execution."""

    def __init__(self) -> None:
        self.saver = MemorySaver()

    def get_config(self, thread_id: str, checkpoint_id: str) -> dict:
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "checkpoint_ns": "",
            }
        }

    def put(self, thread_id: str, checkpoint_id: str, state: dict) -> None:
        config = self.get_config(thread_id, checkpoint_id)
        self.saver.put(config, state, metadata={"tick": checkpoint_id}, new_versions={})

    def get(self, thread_id: str, checkpoint_id: str) -> dict | None:
        config = self.get_config(thread_id, checkpoint_id)
        return self.saver.get(config)

    def latest(self, thread_id: str) -> dict | None:
        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        return self.saver.get(config)
