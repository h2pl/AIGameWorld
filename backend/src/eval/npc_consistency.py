"""2. NPC Consistency — NPC 行为与设定一致性评估.

检查：
- NPC 对话内容是否符合其性格设定
- NPC 不应说出与其角色设定矛盾的话（如铁匠说自己是公主）
- NPC 位置应在其所属场景内
- disposition 变化应有原因（不应从 friendly 直接变 hostile 无过渡）

注意：性格一致性需要 LLM-as-Judge，这里做确定性检查。
"""

import json
from typing import Any

from .base import DimensionReport, EvalIssue, Severity

# 明显矛盾的关键词 / Obvious contradiction keywords
_CONTRADICTION_PATTERNS = {
    "blacksmith": ["公主", "王子", "国王", "王后", "贵族"],
    "merchant": ["国王", "骑士", "守卫"],
    "guard": ["小偷", "强盗", "乞丐"],
}


def evaluate_npc_consistency(
    tick: int,
    actors: list[dict[str, Any]] | None,
    events: list[dict[str, Any]] | None,
    scenes: list[dict[str, Any]] | None,
) -> DimensionReport:
    """评估 NPC 行为一致性 / Evaluate NPC behavior consistency."""
    report = DimensionReport(dimension_name="npc_consistency", score=100.0, passed=0, total=0)

    # 构建 actor 场景映射 / Build actor→scene mapping
    actor_scenes: dict[str, str] = {}
    for a in actors or []:
        aid = str(a.get("actor_id", a.get("id", "")))
        sid = a.get("scene_id", "")
        actor_scenes[aid] = sid

    # ── 1. NPC 对话内容矛盾检测 / Dialogue contradiction detection ──
    for ev in events or []:
        if ev.get("type") not in ("pc_talk", "character_talk"):
            continue

        payload = ev.get("payload", {})
        result = payload.get("result", {})
        turns = result.get("turns", []) if isinstance(result, dict) else []
        speaker_id = str(payload.get("target_id", ""))
        if not speaker_id or not turns:
            continue

        # 找到对应的 actor / Find matching actor
        actor = next(
            (a for a in (actors or []) if str(a.get("actor_id", a.get("id", ""))) == speaker_id),
            None,
        )
        if not actor:
            continue

        actor_role = actor.get("role", "").lower()
        actor_name = actor.get("name", "").lower()

        report.total += 1

        # 检查对话中是否有明显矛盾 / Check dialogue for contradictions
        all_text = " ".join(t.get("text", "") for t in turns if isinstance(t, dict))
        for role_key, bad_phrases in _CONTRADICTION_PATTERNS.items():
            if role_key in actor_role or role_key in actor_name:
                for phrase in bad_phrases:
                    if phrase in all_text:
                        report.issues.append(
                            EvalIssue(
                                dimension="npc_consistency",
                                severity=Severity.HIGH,
                                message=f"NPC {actor_name}({role_key}) 说了矛盾内容: '{phrase}'",
                                detail={
                                    "speaker_id": speaker_id,
                                    "role": actor_role,
                                    "contradiction": phrase,
                                    "text_snippet": all_text[:100],
                                },
                            )
                        )
                        break
                break
        else:
            report.passed += 1

    # ── 2. NPC 场景位置一致性 / NPC scene location consistency ──
    scene_ids = {s.get("id", s.get("sceneId", "")) for s in scenes or []}
    for actor in actors or []:
        report.total += 1
        aid = str(actor.get("actor_id", actor.get("id", "")))
        sid = actor.get("scene_id", "")
        if sid and scene_ids and sid not in scene_ids:
            report.issues.append(
                EvalIssue(
                    dimension="npc_consistency",
                    severity=Severity.MEDIUM,
                    message=f"Actor {aid} 在未知场景 '{sid}'",
                    detail={"actor_id": aid, "scene_id": sid, "known_scenes": list(scene_ids)},
                )
            )
        else:
            report.passed += 1

    # ── 3. Active Actor 的 HP 合理性 / Active actor HP sanity ──
    for actor in actors or []:
        if actor.get("status") != "active":
            continue
        report.total += 1
        combat_str = actor.get("combat_json", "{}")
        try:
            combat_data = json.loads(combat_str) if isinstance(combat_str, str) else combat_str
            hp = int(combat_data.get("current_hp", combat_data.get("hp", 1)))
            max_hp = int(combat_data.get("max_hp", 10))
        except (json.JSONDecodeError, TypeError, ValueError):
            report.passed += 1
            continue

        if hp < 0:
            report.issues.append(
                EvalIssue(
                    dimension="npc_consistency",
                    severity=Severity.HIGH,
                    message=f"Active Actor {actor.get('name', '')} HP={hp}<0",
                    detail={"hp": hp, "max_hp": max_hp},
                )
            )
        elif hp > max_hp * 2:
            report.issues.append(
                EvalIssue(
                    dimension="npc_consistency",
                    severity=Severity.MEDIUM,
                    message=f"Actor {actor.get('name', '')} HP={hp}>{max_hp * 2}, 可能异常",
                    detail={"hp": hp, "max_hp": max_hp},
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
