"""4. Event Causality & Memory — 事件因果性与记忆一致性评估.

检查：
- 事件时序：dm_create → pc_decision → actions → dm_narrative
- 记忆因果：如果 tick N 有对话事件，NPC 的记忆中应包含该对话
- 反思触发：连续 N tick 后应触发反思（reflection_interval）
"""

from typing import Any

from .base import DimensionReport, EvalIssue, Severity


def evaluate_event_causality(
    tick: int,
    events: list[dict[str, Any]] | None,
    memories: list[dict[str, Any]] | None,
    reflection_interval: int = 5,
) -> DimensionReport:
    """评估事件因果性和记忆一致性 / Evaluate event causality and memory consistency."""
    report = DimensionReport(
        dimension_name="causality_memory",
        score=100.0,
        passed=0,
        total=0,
    )

    if not events:
        return report

    # ── 1. 核心事件时序 / Core event ordering ──
    idx_map: dict[str, int] = {}
    for i, ev in enumerate(events):
        etype = ev.get("type", "")
        if etype not in idx_map:
            idx_map[etype] = i

    expected_order = [
        ("dm_create", "pc_decision"),
        ("pc_decision", "dm_narrative"),
        ("dm_create", "dm_narrative"),
    ]
    for before_type, after_type in expected_order:
        report.total += 1
        before_idx = idx_map.get(before_type)
        after_idx = idx_map.get(after_type)

        if before_idx is not None and after_idx is not None and before_idx > after_idx:
            report.issues.append(
                EvalIssue(
                    dimension="causality_memory",
                    severity=Severity.HIGH,
                    message=f"事件顺序错误: {after_type}(idx={after_idx}) 出现在 {before_type}(idx={before_idx}) 之前",
                    detail={
                        "before": before_type,
                        "after": after_type,
                        "before_idx": before_idx,
                        "after_idx": after_idx,
                    },
                )
            )
        else:
            report.passed += 1

    # ── 2. dm_narrative 应在所有 action 之后 / dm_narrative after all actions ──
    action_types = {"pc_talk", "pc_explore", "pc_interact", "pc_combat", "character_move"}
    narr_idx = idx_map.get("dm_narrative")
    if narr_idx is not None:
        for atype in action_types:
            aidx = idx_map.get(atype)
            if aidx is not None:
                report.total += 1
                if aidx > narr_idx:
                    report.issues.append(
                        EvalIssue(
                            dimension="causality_memory",
                            severity=Severity.HIGH,
                            message=f"{atype}(idx={aidx}) 出现在 dm_narrative(idx={narr_idx}) 之后",
                            detail={
                                "action_type": atype,
                                "action_idx": aidx,
                                "narrative_idx": narr_idx,
                            },
                        )
                    )
                else:
                    report.passed += 1

    # ── 3. 记忆存在性检查 / Memory existence check ──
    talk_events = [e for e in events if e.get("type") in ("pc_talk", "character_talk")]
    if talk_events and memories is not None:
        talk_targets = set()
        for ev in talk_events:
            p = ev.get("payload", {})
            tid = str(p.get("target_id", ""))
            if tid:
                talk_targets.add(tid)

        report.total += 1
        memory_entities = {str(m.get("pc_id", m.get("entity_id", ""))) for m in memories}
        if talk_targets and not talk_targets.intersection(memory_entities):
            # 如果有对话但对应实体无记忆记录，可能遗漏 / Dialog without memory record
            report.issues.append(
                EvalIssue(
                    dimension="causality_memory",
                    severity=Severity.LOW,
                    message=f"对话涉及实体 {list(talk_targets)} 但记忆中未找到对应记录",
                    detail={
                        "talk_targets": list(talk_targets),
                        "memory_entities": list(memory_entities)[:10],
                    },
                )
            )
        else:
            report.passed += 1

    # ── 4. 反思触发周期 / Reflection trigger cycle ──
    if tick > 0 and tick % reflection_interval == 0:
        report.total += 1
        has_reflection = any(e.get("type") == "reflection" for e in events)
        if not has_reflection:
            report.issues.append(
                EvalIssue(
                    dimension="causality_memory",
                    severity=Severity.LOW,
                    message=f"Tick {tick} 是反思间隔点（每{reflection_interval}tick）但未触发反思事件",
                    detail={"tick": tick, "reflection_interval": reflection_interval},
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
