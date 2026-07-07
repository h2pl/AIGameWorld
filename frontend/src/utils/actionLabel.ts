/** 动作类型 → 语义通顺的中文标签 / Action type → natural Chinese label */

import type { EventData } from "../types";

/**
 * @param actionType 动作类型 / Action type: talk | interact | combat | explore | wait
 * @param targetId 目标 id（可选）/ Target id (optional)
 * @param position 探索座标（可选）/ Position for explore (optional)
 * @returns 语义自然的中文标签 / Natural Chinese phrase
 */
export function actionLabel(
  actionType: string,
  targetId?: string,
  position?: { x: number; y: number }
): string {
  switch (actionType) {
    case "talk":
      return targetId ? `与 ${targetId} 对话` : "交谈";
    case "interact":
      return targetId ? `与 ${targetId} 交互` : "交互";
    case "combat":
      return targetId ? `与 ${targetId} 战斗` : "战斗";
    case "explore":
      return position ? `探索(${position.x}, ${position.y})` : "探索";
    case "wait":
      return "原地等待";
    default:
      return actionType;
  }
}

/** pc_decision 事件 → 面板摘要文本 / pc_decision event → panel summary text */
export function decisionSummary(ev: EventData): string {
  const p = ev.payload || {};
  const pcName = String(p.pc_name || p.pc_id || "");
  const action = String(p.action_type || "wait");
  const targetId = p.target_id ? String(p.target_id) : undefined;
  const px = p.position_x !== undefined ? Number(p.position_x) : undefined;
  const py = p.position_y !== undefined ? Number(p.position_y) : undefined;
  const position = px !== undefined && py !== undefined ? { x: px, y: py } : undefined;
  const thought = String(p.thought || "");
  const label = actionLabel(action, targetId, position);
  const body = `【${pcName}】${label}`;
  return thought ? `${body} · ${_trunc(thought, 24)}` : body;
}

function _trunc(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}
