"""Phase 3 Service: 唤醒 PC + Actor 决策协调。"""
from typing import Any

from .character_service import pc_decide, actor_decide


def character_decide(state: dict[str, Any]) -> dict[str, Any]:
    """唤醒 DM 指定的 PC + Actor。后续 M5 改为 Send fan-out 并行。"""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    actions = []

    for pc_id in direction.get("featured_pcs", []):
        r = pc_decide({"pc_id": pc_id, "plot_brief": plot_brief})
        if r.get("action_out"):
            actions.append(r["action_out"])

    for actor_id in direction.get("featured_actors", []):
        r = actor_decide({"actor_id": actor_id, "plot_brief": plot_brief})
        if r.get("action_out"):
            actions.append(r["action_out"])

    return {"character_actions": actions}
