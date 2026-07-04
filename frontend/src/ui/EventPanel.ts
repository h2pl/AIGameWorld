/** 事件面板 / Event Panel — 只展示当前 tick 的事件，切换 tick 时刷新 */
import { Panel } from "./Panel";
import { gameStore, type GameState } from "../state/GameStore";
import type { EventData } from "../types";

/** 事件类型 → 图标 / Event type → icon */
const EVENT_ICONS: Record<string, string> = {
  dm_create: "🎲",
  dm_narrative: "📖",
  scene_setup: "🗺️",
  scene_objects: "📦",
  character_move: "🚶",
  character_talk: "🗣️",
  pc_talk: "🗣️",
  character_explore: "🔍",
  combat_event: "⚔️",
  game_event: "🎮",
  state_change: "🔄",
};

export class EventPanel extends Panel {
  private listEl!: HTMLElement; // 事件列表容器 / Event list container
  private tickBadgeEl!: HTMLElement; // Tick 徽章 / Tick badge
  private currentTick = 0; // 当前展示的 tick / Currently displayed tick
  /** 当前 tick 内已渲染的最后一个 seq */
  private renderedSeq = 0;

  constructor() {
    super("event-panel");
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
    // 历史按钮点击 → 派发事件 / History button click → dispatch event
    el.querySelector("#event-history-btn")!.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("show-event-history"));
    });
    return el;
  }

  protected bindStore(): void {
    this.unsubscribe = gameStore.subscribe((s: GameState) => {
      this.onStateChange(s);
    });
  }

  private onStateChange(state: GameState): void {
    // tick 切换时清空面板，重置已渲染 seq / Clear panel on tick change
    if (state.display_tick !== this.currentTick) {
      this.currentTick = state.display_tick;
      this.listEl.innerHTML = "";
      this.renderedSeq = 0;
      this.tickBadgeEl.textContent = `Display_Tick=${this.currentTick}`;
      if (this.currentTick === 0) {
        this.listEl.innerHTML = `<div class="event-empty">等待开始...</div>`;
      }
    }

    console.log("[EventPanel] stateChange tick=%d events=%d", this.currentTick, state.events?.length || 0, state.events?.map(e => ({t: e.type, tick: e.tick, seq: e.seq})));
    if (!state.events || state.events.length === 0) return;

    // 只渲染当前 tick 且 seq > renderedSeq 的新事件 / Only render current tick's new events
    const newEvents = state.events.filter(
      (ev) => ev.tick === this.currentTick && (ev.seq ?? 0) > this.renderedSeq,
    );
    console.log("[EventPanel] newEvents=%d renderedSeq=%d", newEvents.length, this.renderedSeq);
    if (newEvents.length === 0) return;

    // 首次有事件时移除空状态提示 / Remove empty state on first event
    if (this.listEl.querySelector(".event-empty")) {
      this.listEl.innerHTML = "";
    }

    const frag = document.createDocumentFragment();
    for (const ev of newEvents) {
      if (ev.seq) this.renderedSeq = Math.max(this.renderedSeq, ev.seq);
      frag.appendChild(this._createLine(ev));
    }

    const shouldScroll = this._shouldAutoScroll();
    this.listEl.appendChild(frag);
    if (shouldScroll) {
      this.listEl.scrollTop = this.listEl.scrollHeight;
    }
  }

  /** 创建单条事件 DOM — 前缀用事件类型中文名，内容用 payload */
  private _createLine(ev: EventData): HTMLElement {
    const icon = EVENT_ICONS[ev.type] || "📌";
    const typeLabel = _readableType(ev.type);
    const content = _formatPayload(ev);
    const el = document.createElement("div");
    el.className = "event-line";
    el.innerHTML = `<span class="event-icon">${icon}</span><span class="event-type">${typeLabel}</span><span class="event-content">${content}</span>`;
    return el;
  }

  /** 用户没有手动上滚时才自动到底 / Auto-scroll only if user hasn't scrolled up */
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
    pc_talk: "角色对话",
    character_explore: "角色探索",
    combat_event: "战斗事件",
    game_event: "游戏事件",
    state_change: "状态变更",
  };
  return map[t] || t;
}

/** 格式化 payload 为可读文本 / Format payload to readable text */
function _formatPayload(ev: EventData): string {
  let payload: Record<string, unknown> = ev.payload || {};

  // appendEvent 会把 payload 序列化到 description；优先用原始 payload / Raw payload preferred
  if (!payload && ev.description) {
    try {
      payload = JSON.parse(ev.description);
    } catch {
      return ev.description;
    }
  }

  // 按事件类型提取关键信息 / Extract key info by event type
  switch (ev.type) {
    case "dm_create":
      return String(payload.plot_brief || payload.scene_id || "");
    case "dm_narrative":
      return String(payload.text || payload.narrative || "");
    case "scene_setup":
      return String(payload.scene_id || "");
    case "character_talk":
    case "pc_talk": {
      const result = payload.result as Record<string, unknown> | undefined;
      const turns = (result?.turns ?? []) as Array<{ speaker_id: string; text: string }>;
      if (turns.length) {
        return turns.map((t) => `${t.speaker_id}: ${t.text}`).join("；");
      }
      const pc = payload.pc_id || payload.character_id || "";
      const fallback = result?.text || result?.content || "";
      return `${pc}: ${fallback}`;
    }
    case "character_move": {
      const pc = payload.pc_id || "";
      const pos = `(${payload.x || 0}, ${payload.y || 0})`;
      return `${pc} → ${pos}`;
    }
    default:
      return JSON.stringify(payload).slice(0, 80);
  }
}
