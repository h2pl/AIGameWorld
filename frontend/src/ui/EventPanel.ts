// --- 事件面板 / Event Panel ---
// --- 通过 window tick-event 消费 ---
// --- / ---
// --- 渲染 + HUD / Render + HUD ---
// -- file start -- / file start
/** 事件面板 / Event Panel — 仅通过 window 事件消费，不订阅 store */
import { Panel } from "./Panel";
import type { EventData } from "../types";

const EVENT_ICONS: Record<string, string> = {
  dm_create: "🎲", dm_narrative: "📖", scene_setup: "🗺️", scene_objects: "📦",
  character_move: "🚶", pc_explore: "🔍", character_talk: "🗣️", pc_talk: "🗣️",
  character_explore: "🔍", combat_event: "⚔️", game_event: "🎮", state_change: "🔄",
};

export class EventPanel extends Panel {
  private listEl!: HTMLElement;
  private tickBadgeEl!: HTMLElement;
  private currentTick = 0;
  private _onTickStart: (e: Event) => void;
  private _onTickEvent: (e: Event) => void;

  constructor() {
    super("event-panel");
    this._onTickStart = (e: Event) => this._clearPanel(e);
    this._onTickEvent = (e: Event) => this._handleTickEvent((e as CustomEvent).detail);
  }

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
      <div class="panel-body event-body"></div>
    `;
    this.listEl = el.querySelector(".event-body")!;
    this.tickBadgeEl = el.querySelector("#event-tick-badge")!;
    el.querySelector("#event-history-btn")!.addEventListener("click", () =>
      window.dispatchEvent(new CustomEvent("show-event-history")));
    return el;
  }

  protected bindStore(): void {
    window.addEventListener("tick-start", this._onTickStart);
    window.addEventListener("tick-event", this._onTickEvent);
  }

  private _clearPanel(e: Event): void {
    const tick = (e as CustomEvent).detail.tick as number;
    this.tickBadgeEl.textContent = `Display_Tick=${tick}`;
    this.currentTick = tick;
    this.listEl.innerHTML = tick === 0
      ? `<div class="event-empty">等待开始...</div>`
      : "";
  }

  private _handleTickEvent(detail: { type: string; payload: Record<string, unknown>; phase?: "done" }): void {
    if (detail.phase === "done") {
      const a = this.listEl.querySelector(".event-active");
      if (a) a.classList.remove("event-active");
      return;
    }

    const ev: EventData = { type: detail.type, tick: 0, payload: detail.payload };
    if (this.listEl.querySelector(".event-empty")) this.listEl.innerHTML = "";

    const prev = this.listEl.querySelector(".event-active");
    if (prev) prev.classList.remove("event-active");

    const line = this._createLine(ev);
    line.classList.add("event-active");
    this.listEl.appendChild(line);
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }

  private _createLine(ev: EventData): HTMLElement {
    const icon = EVENT_ICONS[ev.type] || "📌";
    const content = _formatPayload(ev);
    const el = document.createElement("div");
    el.className = "event-line";
    el.innerHTML = `<span class="event-icon">${icon}</span><span class="event-type">${_readableType(ev.type)}</span><span class="event-content">${content}</span>`;
    return el;
  }

  private _shouldAutoScroll(): boolean {
    const { scrollTop, clientHeight, scrollHeight } = this.listEl;
    return scrollTop + clientHeight >= scrollHeight - 12;
  }

  destroy(): void {
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    super.destroy();
  }
}

function _readableType(t: string): string {
  const map: Record<string, string> = {
    dm_create: "DM 创建情境", dm_narrative: "DM 叙事", scene_setup: "场景设置",
    pc_explore: "角色探索", pc_talk: "角色对话", pc_interact: "角色互动",
    character_move: "角色移动", combat_event: "战斗事件", state_change: "状态变更",
  };
  return map[t] || t;
}

function _formatPayload(ev: EventData): string {
  const p = ev.payload || {};
  switch (ev.type) {
    case "dm_create": return String(p.plot_brief || p.scene_id || "");
    case "dm_narrative": return String(p.text || p.narrative || "");
    case "scene_setup": return String(p.scene_id || "");
    case "pc_explore": case "character_explore":
      const wp = p.waypoints as Array<{ x: number; y: number }> | undefined;
      if (wp?.length) return wp.map(w => `(${w.x},${w.y})`).join(" → ");
      return "探索";
    case "pc_talk": case "character_talk": {
      const r = p.result as Record<string, unknown> | undefined;
      const turns = (r?.turns ?? []) as Array<{ speaker_id: string; text: string }>;
      if (turns.length) return turns.map(t => `${t.speaker_id}: ${t.text}`).join("；");
      return `${p.pc_id || ""}: ${r?.text || r?.content || ""}`;
    }
    default: return JSON.stringify(p).slice(0, 80);
  }
}
