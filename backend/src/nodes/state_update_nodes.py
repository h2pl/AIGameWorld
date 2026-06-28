"""State Update Node: Phase 5 — 合并结果更新状态 / Merge results and update state."""
from typing import Any


def state_update_node(state: dict[str, Any]) -> dict[str, Any]:
    """合并所有 Phase 结果，产出 state_diff + cast_changes。

    后续接入 WorldStateStore 写入 / Future: write via WorldStateStore.
    """
    return {"state_diff": {}, "cast_changes": []}
