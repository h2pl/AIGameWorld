/** 事件面板 / Event Panel — 展示 tick 事件日志，增量追加，保留最近 50 条 */
import { Panel } from "./Panel";
import { gameStore, type GameState } from "../state/GameStore";
import type { EventData } from "../types";

/** 事件类型 → 图标 / Event type → icon */
const EVENT_ICONS: Record<string, string> = {
  combat: "⚔️",
  dialogue: "🗣️",
  exploration: "🔍",
  quest: "📜",
  system: "⚙️",
};

export class EventPanel extends Panel {
  private listEl!: HTMLElement;
  private seenIds = new Set<string>();
  private $max = 50; // 最多保留 50 条 / Max events

  constructor() {
    super("event-panel");
  }

  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel event-panel";
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">📋</span>
        <span class="panel-title">事件 / Events</span>
        <span class="panel-count" id="event-count">0</span>
      </div>
      <div class="panel-body event-body"></div>
    `;
    this.listEl = el.querySelector(".event-body")!;
    return el;
  }

  protected bindStore(): void {
    this.unsubscribe = gameStore.subscribe((s: GameState) => {
      this.onStateChange(s);
    });
  }

  private onStateChange(state: GameState): void {
    if (!state.events || state.events.length === 0) return;
    let changed = false;
    for (const ev of state.events) {
      const key = `${ev.type}:${ev.description || ""}:${ev.source || ""}`;
      if (this.seenIds.has(key)) continue;
      this.seenIds.add(key);
      this.appendEvent(ev);
      changed = true;
    }
    // 清理超出上限的旧事件 / Trim old events
    while (this.seenIds.size > this.$max) {
      const first = this.listEl.firstElementChild;
      if (first) first.remove();
      else break;
    }
    if (changed) {
      const countEl = document.getElementById("event-count");
      if (countEl) countEl.textContent = String(this.listEl.children.length);
    }
  }

  private appendEvent(ev: EventData): void {
    const icon = EVENT_ICONS[ev.type] || "•";
    const desc = ev.description || ev.type;
    const el = document.createElement("div");
    el.className = "event-line";
    el.textContent = `${icon} ${desc}`;
    this.listEl.appendChild(el);
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }
}
