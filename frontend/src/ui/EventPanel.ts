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
      const key = `${ev.tick || 0}:${ev.type}:${ev.description || ""}`;
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
    const icon = EVENT_ICONS[ev.type] || "📌";
    const tick = ev.tick ? `[Tick ${ev.tick}]` : "";
    const el = document.createElement("div");
    el.className = "event-line";
    el.textContent = `${tick} ${icon} ${_readableType(ev.type)}`;
    this.listEl.appendChild(el);
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }
}

/** 事件类型中文名 / Readable event type names */
function _readableType(t: string): string {
  const map: Record<string, string> = {
    dm_create: "DM 创建情境",
    dm_narrative: "DM 叙事",
    scene_setup: "场景设置",
    scene_objects: "场景物体",
    character_move: "角色移动",
    character_talk: "角色对话",
    character_explore: "角色探索",
    combat_event: "战斗事件",
    game_event: "游戏事件",
    state_change: "状态变更",
  };
  return map[t] || t;
}
