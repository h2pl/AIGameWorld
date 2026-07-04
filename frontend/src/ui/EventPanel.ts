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
  /** 已处理的最后一个 seq，只追加 seq > lastSeq 的事件 */
  private lastSeq = 0;
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

    // 只处理 seq > lastSeq 的新事件，避免重复插入
    const newEvents = state.events.filter(
      (ev) => (ev.seq ?? 0) > this.lastSeq,
    );
    if (newEvents.length === 0) return;

    const frag = document.createDocumentFragment();
    for (const ev of newEvents) {
      if (ev.seq) this.lastSeq = Math.max(this.lastSeq, ev.seq);
      frag.appendChild(this._createLine(ev));
    }

    const shouldScroll = this._shouldAutoScroll();
    this.listEl.appendChild(frag);
    this._trim();
    if (shouldScroll) {
      this.listEl.scrollTop = this.listEl.scrollHeight;
    }
    const countEl = document.getElementById("event-count");
    if (countEl) countEl.textContent = String(this.listEl.children.length);
  }

  private _createLine(ev: EventData): HTMLElement {
    const icon = EVENT_ICONS[ev.type] || "📌";
    const tick = ev.tick ? `[Tick ${ev.tick}]` : "";
    const el = document.createElement("div");
    el.className = "event-line";
    el.textContent = `${tick} ${icon} ${_readableType(ev.type)}`;
    el.title = ev.description || _readableType(ev.type);
    return el;
  }

  /** 裁剪超出上限的旧 DOM */
  private _trim(): void {
    while (this.listEl.children.length > this.$max) {
      this.listEl.removeChild(this.listEl.firstElementChild!);
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
