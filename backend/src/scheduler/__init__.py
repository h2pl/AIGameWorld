"""调度层 / Scheduler Layer.

独立于主 tick 链路：轮询 dm_records + events，异步写 ChromaDB + 触发摘要。
"""
