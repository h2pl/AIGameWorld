"""1. World State Correctness — 世界状态正确性评估.

检查：
- 战斗后 HP 是否合理（被击败的 target HP=0）
- PC 坐标是否在地图边界内
- PC ID 不重复
- Actor 状态一致性（active 但 HP=0 应报错）
"""

import json
from typing import Any

from .base import DimensionReport, EvalIssue, Severity


def evaluate_world_state(
    tick: int,
    pcs: list[dict[str, Any]] | None,
    actors: list[dict[str, Any]] | None,
    events: list[dict[str, Any]] | None,
    scenes: list[dict[str, Any]] | None,
) -> DimensionReport:
    """评估世界状态正确性 / Evaluate world state correctness."""
    report = DimensionReport(
        dimension_name="world_state",
        score=100.0,
        passed=0,
        total=0,
    )
    max_w = 200
    max_h = 200
    if scenes:
        for s in scenes:
            mw = s.get("map_width", s.get("mapW", 200))
            mh = s.get("map_height", s.get("mapH", 200))
            if mw > 0 and mw < max_w:
                max_w = mw
            if mh > 0 and mh < max_h:
                max_h = mh

    # ── 1. PC 坐标合法性 / PC position validity ──
    for pc in pcs or []:
        report.total += 1
        px = pc.get("position_x", pc.get("positionX", 0))
        py = pc.get("position_y", pc.get("positionY", 0))

        if (
            isinstance(px, int)
            and px >= 0
            and px <= max_w
            and isinstance(py, int)
            and py >= 0
            and py <= max_h
        ):
            report.passed += 1
        elif isinstance(px, int) and isinstance(py, int):
            report.issues.append(
                EvalIssue(
                    dimension="world_state",
                    severity=Severity.CRITICAL,
                    message=f"PC {pc.get('pc_id', '?')} 坐标越界 ({px},{py})",
                    detail={"x": px, "y": py, "max_w": max_w, "max_h": max_h},
                )
            )
        else:
            report.passed += 1

    # ── 2. Actor 坐标合法性 / Actor position validity ──
    for actor in actors or []:
        report.total += 1
        ax = actor.get("position_x", actor.get("positionX", 0))
        ay = actor.get("position_y", actor.get("positionY", 0))
        aid = actor.get("actor_id", actor.get("id", ""))

        if (
            isinstance(ax, int)
            and ax >= 0
            and ax <= max_w
            and isinstance(ay, int)
            and ay >= 0
            and ay <= max_h
        ):
            report.passed += 1
        elif isinstance(ax, int) and isinstance(ay, int):
            report.issues.append(
                EvalIssue(
                    dimension="world_state",
                    severity=Severity.HIGH,
                    message=f"Actor {aid} 坐标越界 ({ax},{ay})",
                    detail={"x": ax, "y": ay, "actor_id": aid},
                )
            )
        else:
            report.passed += 1

    # ── 3. 被击败目标状态一致性 / Defeated target state consistency ──
    defeated_ids: set[str] = set()
    for ev in events or []:
        payload = ev.get("payload", {})
        if ev.get("type") == "pc_combat" and payload.get("target_defeated"):
            tid = str(payload.get("target_id", ""))
            if tid:
                defeated_ids.add(tid)

    if defeated_ids:
        for actor in actors or []:
            aid = str(actor.get("actor_id", actor.get("id", "")))
            if aid not in defeated_ids:
                continue
            report.total += 1
            combat_json_str = actor.get("combat_json", "{}")
            try:
                combat_data = (
                    json.loads(combat_json_str)
                    if isinstance(combat_json_str, str)
                    else combat_json_str
                )
                hp = int(combat_data.get("current_hp", combat_data.get("hp", 1)))
            except (json.JSONDecodeError, TypeError, ValueError):
                hp = 1

            if hp > 0:
                report.issues.append(
                    EvalIssue(
                        dimension="world_state",
                        severity=Severity.CRITICAL,
                        message=f"Actor {aid} 标记击败但 HP={hp}>0",
                        detail={"actor_id": aid, "hp": hp},
                    )
                )
            else:
                report.passed += 1

    # ── 4. PC ID 不重复 / No duplicate PC IDs ──
    report.total += 1
    pc_ids = [str(p.get("pc_id", p.get("id", ""))) for p in pcs or []]
    if len(pc_ids) != len(set(pc_ids)):
        report.issues.append(
            EvalIssue(
                dimension="world_state",
                severity=Severity.CRITICAL,
                message=f"PC 列表存在重复 ID: {pc_ids}",
            )
        )
    else:
        report.passed += 1

    # 计算分数 / Calculate score
    penalty = sum(
        {Severity.CRITICAL: 30, Severity.HIGH: 15, Severity.MEDIUM: 5, Severity.LOW: 1}.get(
            i.severity, 0
        )
        for i in report.issues
    )
    report.score = max(0.0, 100.0 - penalty)
    return report
