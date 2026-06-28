"""State Update Service: Phase 5 — 合并结果更新状态 / Merge results and update state."""
from typing import Any

from ..graph.state import OverallState


def state_update(state: OverallState) -> dict[str, Any]:
    """合并所有 Phase 结果，产出 state_diff + cast_changes。

    后续接入 WorldStateStore 写入 / Future: write via WorldStateStore.
    产出 / Outputs: state_diff, cast_changes
    """
    return {"state_diff": {}, "cast_changes": []}  # ③ M3 mock: 直接返回空

