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
  /** key -> DOM 元素，保证去重与裁剪同步 */
  private seen = new Map<string, HTMLElement>();
  /** 有序的 key 列表，用于从头裁剪 */
  private keys: string[] = [];
  private $max = 50; // 面板最多保留 50 条 / Max events in panel

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

    // 批量插入减少重排 / Batch insert to reduce reflow
    const frag = document.createDocumentFragment();
    let changed = false;
    for (const ev of state.events) {
      const key = this._makeKey(ev);
      if (this.seen.has(key)) continue;
      const el = this._createLine(ev, key);
      this.seen.set(key, el);
      this.keys.push(key);
      frag.appendChild(el);
      changed = true;
    }

    if (changed) {
      const shouldScroll = this._shouldAutoScroll();
      this.listEl.appendChild(frag);
      this._trim();
      if (shouldScroll) {
        this.listEl.scrollTop = this.listEl.scrollHeight;
      }
      const countEl = document.getElementById("event-count");
      if (countEl) countEl.textContent = String(this.listEl.children.length);
    }
  }

  private _makeKey(ev: EventData): string {
    // 用索引避免 description 重复导致的新事件被吞
    return `${ev.tick || 0}:${ev.type}:${this.seen.size}`;
  }

  private _createLine(ev: EventData, key: string): HTMLElement {
    const icon = EVENT_ICONS[ev.type] || "📌";
    const tick = ev.tick ? `[Tick ${ev.tick}]` : "";
    const el = document.createElement("div");
    el.className = "event-line";
    el.dataset.key = key;
    el.textContent = `${tick} ${icon} ${_readableType(ev.type)}`;
    el.title = ev.description || _readableType(ev.type);
    return el;
  }

  /** 同步裁剪 DOM 与 seen，避免去重集合无限增长 */
  private _trim(): void {
    while (this.keys.length > this.$max) {
      const key = this.keys.shift();
      if (!key) break;
      const el = this.seen.get(key);
      if (el) el.remove();
      this.seen.delete(key);
    }
  }

  /** 用户没有手动上滚时才自动到底 */
  private _shouldAutoScroll(): boolean {
    const { scrollTop, clientHeight, scrollHeight } = this.listEl;
    return scrollTop + clientHeight >= scrollHeight - 12;
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
