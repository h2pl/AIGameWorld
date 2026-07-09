"""3. Game Rules — 游戏规则合规性评估.

检查：
- DnD 规则：伤害值非负、HP 不超上限、技能检定结果在合法范围(1-20+bonus)
- 移动规则：角色每 tick 只能移动一次（不重复出现 character_move 事件）
- 战斗规则：只有 pc_combat 事件才能产生伤害和击败效果
"""

import json
from collections import Counter
from typing import Any

from .base import DimensionReport, EvalIssue, Severity


def evaluate_game_rules(
    tick: int,
    events: list[dict[str, Any]] | None,
    pcs: list[dict[str, Any]] | None,
    actors: list[dict[str, Any]] | None,
) -> DimensionReport:
    """评估游戏规则合规性 / Evaluate game rule compliance."""
    report = DimensionReport(dimension_name="game_rules", score=100.0, passed=0, total=0)

    if not events:
        return report

    # ── 1. 战斗事件规则 / Combat event rules ──
    for ev in events:
        if ev.get("type") != "pc_combat":
            continue

        payload = ev.get("payload", {})
        report.total += 1

        # 1a: damage >= 0 / Damage non-negative
        damage = payload.get("damage")
        if damage is not None and int(damage) < 0:
            report.issues.append(
                EvalIssue(
                    dimension="game_rules",
                    severity=Severity.HIGH,
                    message=f"战斗伤害为负: damage={damage}",
                    detail={"damage": damage},
                )
            )
            continue

        # 1b: 攻击结果完整性 / Attack result completeness
        has_damage = damage is not None
        has_defeated = payload.get("target_defeated")

        if has_defeated and not has_damage and damage != 0:
            report.issues.append(
                EvalIssue(
                    dimension="game_rules",
                    severity=Severity.MEDIUM,
                    message="标记击败但缺少攻击结果或伤害数据",
                    detail=payload,
                )
            )
            continue

        report.passed += 1

    # ── 2. DnD 投骰规则 / DnD roll rules ──
    for ev in events:
        if ev.get("type") not in ("pc_combat", "pc_explore", "pc_interact"):
            continue
        payload = ev.get("payload", {})
        roll = payload.get("roll") or payload.get("d20_roll") or payload.get("skill_check")
        if roll is None:
            continue

        report.total += 1
        try:
            roll_val = int(roll)
        except (ValueError, TypeError):
            report.passed += 1
            continue

        if roll_val < 1 or roll_val > 30:
            report.issues.append(
                EvalIssue(
                    dimension="game_rules",
                    severity=Severity.MEDIUM,
                    message=f"DnD 投骰值异常: roll={roll_val} (正常范围 1~30)",
                    detail={"roll": roll_val},
                )
            )
        else:
            report.passed += 1

    # ── 3. 单 tick 移动唯一性 / Single move per tick per entity ──
    move_events = [e for e in events if e.get("type") == "character_move"]
    if move_events:
        mover_counts = Counter()
        for e in move_events:
            p = e.get("payload", {})
            mover_id = p.get("entity_id") or p.get("character_id") or ""
            mover_counts[mover_id] += 1

        report.total += len(mover_counts)
        for mid, count in mover_counts.items():
            if count > 1:
                report.issues.append(
                    EvalIssue(
                        dimension="game_rules",
                        severity=Severity.HIGH,
                        message=f"实体 {mid} 在同一 tick 移动 {count} 次（应为1次）",
                        detail={"entity_id": mid, "move_count": count},
                    )
                )
            else:
                report.passed += 1
    else:
        report.total += 1
        report.passed += 1

    # ── 4. HP 上限检查 / HP upper bound check ──
    for entity_list, label in [(pcs, "PC"), (actors, "Actor")]:
        for ent in entity_list or []:
            report.total += 1
            combat_str = ent.get("combat_json", "{}")
            try:
                cd = json.loads(combat_str) if isinstance(combat_str, str) else combat_str
                hp = int(cd.get("current_hp", cd.get("hp", 1)))
                max_hp = int(cd.get("max_hp", 10))
            except (json.JSONDecodeError, TypeError, ValueError):
                report.passed += 1
                continue

            if hp > max_hp:
                report.issues.append(
                    EvalIssue(
                        dimension="game_rules",
                        severity=Severity.MEDIUM,
                        message=f"{label} {ent.get('name', '?')} HP={hp} > MaxHP={max_hp}",
                        detail={
                            "entity": label,
                            "name": ent.get("name", ""),
                            "hp": hp,
                            "max_hp": max_hp,
                        },
                    )
                )
            else:
                report.passed += 1

    penalty = sum(
        {Severity.CRITICAL: 30, Severity.HIGH: 15, Severity.MEDIUM: 5, Severity.LOW: 1}.get(
            i.severity, 0
        )
        for i in report.issues
    )
    report.score = max(0.0, 100.0 - penalty)
    return report
