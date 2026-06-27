"""StorySummarizer 子图 / Story Summarizer Subgraph.
Phase 7: 每 N 步压缩 Event Log → 剧情梗概 / Every N ticks, compress event log into summary.
Mock: 返回未触发. 后续 M4 接入 / Mock: not triggered. M4 integration.
"""

from typing import TypedDict, Any


class SummarizerSubState(TypedDict):
    """摘要器子图状态 / Summarizer subgraph state."""
    events: list[dict[str, Any]]  # 原始事件 / Raw events
    summary_interval: int  # 压缩间隔（每 N tick）/ Compression interval (every N ticks)
    tick: int  # 当前 tick / Current tick
    summary: str  # 摘要文本 / Summary text
    compressed: bool  # 是否触发了压缩 / Whether compression triggered


def summarize_events(state: dict[str, Any]) -> SummarizerSubState:
    """压缩事件为摘要 / Compress events into summary.
    
    Mock: 不触发压缩.
    """
    return SummarizerSubState(
        events=state.get("events", []),
        summary_interval=state.get("summary_interval", 10),
        tick=state.get("tick", 0),
        summary="",
        compressed=False,  # 未触发 / Not triggered yet
    )
