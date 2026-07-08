// --- 事件面板 / Event Panel ---
// --- 通过 window tick-event 消费 ---
// --- / ---
// --- 渲染 + HUD / Render + HUD ---
// -- file start -- / file start
/** 事件面板 / Event Panel — 仅通过 window 事件消费，不订阅 store */
import { Panel } from "./Panel";
import type { EventData } from "../types";
import { actionLabel } from "../utils/actionLabel";

const EVENT_ICONS: Record<string, string> = {
  dm_create: "🎲",
  dm_narrative: "📖",
  scene_setup: "🗺️",
  scene_objects: "📦",
  character_move: "🚶",
  pc_decision: "💡",
  pc_explore: "🔍",
  character_talk: "🗣️",
  pc_talk: "🗣️",
  character_explore: "🔍",
  pc_interact: "🔧",
  pc_combat: "⚔️",
  combat_event: "⚔️",
  game_event: "🎮",
  state_change: "🔄",
};

export class EventPanel extends Panel {
  private listEl!: HTMLElement;
  private tickBadgeEl!: HTMLElement;
  private currentTick = 0;
  private _onTickStart: (e: Event) => void;
  private _onTickEvent: (e: Event) => void;

  /** 构造函数 / Constructor */
  constructor() {
    super("event-panel");
    this._onTickStart = (e: Event) => this._clearPanel(e);
    this._onTickEvent = (e: Event) => this._handleTickEvent((e as CustomEvent).detail);
  }

  /** 构建 DOM 结构 / Build DOM structure */
  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel event-panel";
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">📋</span>
        <span class="panel-title" id="event-title">
          <span>事件/Events</span>
          <span class="event-tick-badge" id="event-tick-badge">Display_Tick=0</span>
        </span>
        <button class="panel-history-btn" id="event-history-btn" title="历史事件">🕓</button>
      </div>
      <div class="panel-body event-body" data-testid="event-list"></div>
    `;
    this.listEl = el.querySelector(".event-body")!;
    this.tickBadgeEl = el.querySelector("#event-tick-badge")!;
    el.querySelector("#event-history-btn")!.addEventListener("click", () =>
      window.dispatchEvent(new CustomEvent("show-event-history"))
    );
    return el;
  }

  /** 绑定窗口事件 / Bind window events */
  protected bindStore(): void {
    window.addEventListener("tick-start", this._onTickStart);
    window.addEventListener("tick-event", this._onTickEvent);
  }

  /** 清空面板并更新 tick 徽章 / Clear panel and update tick badge */
  private _clearPanel(e: Event): void {
    const tick = (e as CustomEvent).detail.tick as number;
    this.tickBadgeEl.textContent = `Display_Tick=${tick}`;
    this.currentTick = tick;
    this.listEl.innerHTML = tick === 0 ? `<div class="event-empty">等待开始...</div>` : "";
  }

  // 内部窗口事件，不展示在事件面板 / Internal window events, skip
  private static _SKIP = new Set(["explore_record", "interact_narration"]);

  /** 处理单个 tick 事件 / Handle single tick event */
  private _handleTickEvent(detail: {
    type: string;
    payload: Record<string, unknown>;
    phase?: "done";
  }): void {
    if (detail.phase === "done") {
      const a = this.listEl.querySelector(".event-active");
      if (a) a.classList.remove("event-active");
      return;
    }
    if (EventPanel._SKIP.has(detail.type)) return;

    const ev: EventData = { type: detail.type, tick: 0, payload: detail.payload };
    if (this.listEl.querySelector(".event-empty")) this.listEl.innerHTML = "";

    const prev = this.listEl.querySelector(".event-active");
    if (prev) prev.classList.remove("event-active");

    const line = this._createLine(ev);
    line.classList.add("event-active");
    this.listEl.appendChild(line);
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }

  /** 创建事件行元素 / Create event line element */
  private _createLine(ev: EventData): HTMLElement {
    const icon = EVENT_ICONS[ev.type] || "📌";
    const content = _formatPayload(ev);
    const el = document.createElement("div");
    el.className = "event-line";
    el.innerHTML = `<span class="event-icon">${icon}</span><span class="event-type">${_readableType(ev.type)}</span><span class="event-content">${content}</span>`;
    return el;
  }

  /** 判断是否需要自动滚动 / Check whether auto-scroll is needed */
  private _shouldAutoScroll(): boolean {
    const { scrollTop, clientHeight, scrollHeight } = this.listEl;
    return scrollTop + clientHeight >= scrollHeight - 12;
  }

  /** 销毁并移除事件监听 / Destroy and remove event listeners */
  destroy(): void {
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    super.destroy();
  }
}

/** 事件类型中文名 / Event type Chinese labels */
function _readableType(t: string): string {
  const map: Record<string, string> = {
    dm_create: "DM 创建情境",
    dm_narrative: "DM 叙事",
    scene_setup: "场景设置",
    scene_objects: "场景物体",
    character_move: "角色移动",
    pc_decision: "角色决策",
    pc_talk: "角色对话",
    character_talk: "角色对话",
    pc_explore: "角色探索",
    character_explore: "角色探索",
    pc_interact: "角色互动",
    pc_combat: "角色战斗",
    combat_event: "战斗事件",
    game_event: "游戏事件",
    state_change: "状态变更",
  };
  return map[t] || t;
}

/** 格式化事件 payload 为可读文本 / Format event payload for display
 *
 * 统一格式：谁做了什么事，中文描述，保持可读性 / Consistent: who did what, Chinese, readable */
function _formatPayload(ev: EventData): string {
  const p = ev.payload || {};
  const pcName = String(p.pc_name || p.pc_id || "");
  switch (ev.type) {
    case "dm_create":
      return String(p.plot_brief || "");
    case "dm_narrative":
      return trunc(String(p.text || p.narrative || ""));
    case "pc_decision": {
      const action = String(p.action_type || "wait");
      const target = p.target_id ? String(p.target_id) : undefined;
      const ex = p.explore_x !== undefined ? Number(p.explore_x) : undefined;
      const ey = p.explore_y !== undefined ? Number(p.explore_y) : undefined;
      const pos = ex !== undefined && ey !== undefined ? { x: ex, y: ey } : undefined;
      const reason = String(p.thought || "");
      const label = actionLabel(action, target, pos);
      return reason ? `【${pcName}】${label} — ${trunc(reason, 30)}` : `【${pcName}】${label}`;
    }
    case "scene_setup":
      return `进入「${String(p.scene_name || p.scene_id || "")}」`;
    case "pc_explore":
    case "character_explore": {
      const record = p.explore_record as string | undefined;
      return record ? `【${pcName}】探索: ${trunc(record, 40)}` : `【${pcName}】四处探索`;
    }
    case "pc_talk":
    case "character_talk": {
      const r = p.result as Record<string, unknown> | undefined;
      const turns = (r?.turns ?? []) as Array<{ speaker_id: string; text: string }>;
      const target = p.target_id ? String(p.target_id) : undefined;
      if (turns.length) {
        const preview = turns.map((t) => trunc(t.text, 12)).join(" / ");
        return `【${pcName}】与${target || "他人"}对话: ${trunc(preview, 50)}`;
      }
      return `【${pcName}】与${target || "他人"}交谈`;
    }
    case "pc_interact": {
      const target = p.target_id ? String(p.target_id) : undefined;
      const narration = (p.narration as string) || "";
      return narration
        ? `【${pcName}】与${target || "物体"}交互: ${trunc(narration, 40)}`
        : `【${pcName}】与${target || "物体"}交互`;
    }
    case "pc_combat": {
      const target = p.target_id ? String(p.target_id) : undefined;
      const narration = (p.narration as string) || "";
      const defeated = p.target_defeated ? "，击败目标" : "";
      return narration
        ? `【${pcName}】与${target || "敌人"}战斗: ${trunc(narration, 40)}${defeated}`
        : `【${pcName}】与${target || "敌人"}战斗${defeated}`;
    }
    case "character_move":
      return `【${pcName}】移动`;
    default:
      return `[${_readableType(ev.type)}]`;
  }
}

function trunc(s: string, n = 30): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}
