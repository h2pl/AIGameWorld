"""Checkpoint 配置 / Checkpoint configuration.

基于 design/03-orchestration-layer.md §4 / Based on orchestration layer design.
使用 LangGraph MemorySaver（内存级），可替换为 SqliteSaver（生产级）。
Uses MemorySaver for development, replaceable with SqliteSaver for production.
"""

from langgraph.checkpoint.memory import MemorySaver


def create_dev_checkpointer() -> MemorySaver:
    """创建开发环境 Checkpointer / Create dev checkpointer.
    
    开发用内存存储，不持久化到磁盘。
    Development uses in-memory storage, no disk persistence.
    """
    return MemorySaver()
