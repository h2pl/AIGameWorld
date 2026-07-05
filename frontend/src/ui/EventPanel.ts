/** 事件面板 / Event Panel
 *
 * 数据来源：直接监听 window "tick-event"，不依赖 GameStore.state.events。
 * Store 仅用于检测 display_tick 变化（触发面板清空）。
 * 历史事件面板（HistoryEventPanel）独立从后端 API 拉取数据。
 *
 * Data source: listens directly to window "tick-event", independent of GameStore.state.events.
 * Store is only used to detect display_tick changes (triggers panel clear).
 * HistoryEventPanel independently fetches from backend API.
 */
import { Panel } from "./Panel";
import { tickStore, type TickState } from "../state/TickStore";
import type { EventData } from "../types";

/** 事件类型 → 图标 / Event type → icon */
const EVENT_ICONS: Record<string, string> = {
  dm_create: "🎲",
  dm_narrative: "📖",
  scene_setup: "🗺️",
  scene_objects: "📦",
  character_move: "🚶",
  pc_explore: "🔍",
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
  /** tick-event 监听器引用，用于 destroy 时移除 / Listener ref for cleanup */
  private _onTickEvent: (e: Event) => void;

  constructor() {
    super("event-panel");
    this._onTickEvent = (e: Event) => {
      this._handleTickEvent((e as CustomEvent).detail);
    };
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
    // 仅订阅 display_tick 变化以清空面板 / Only subscribe to detect tick changes
    this.unsubscribe = tickStore.subscribe((s: TickState) => {
      if (s.display_tick !== this.currentTick) {
        this.currentTick = s.display_tick;
        this.listEl.innerHTML = "";
        this.tickBadgeEl.textContent = `Display_Tick=${this.currentTick}`;
        if (this.currentTick === 0) {
          this.listEl.innerHTML = `<div class="event-empty">等待开始...</div>`;
        }
      }
    });

    // 直接监听 tick-event 获取事件数据 / Listen directly to tick-event for event data
    window.addEventListener("tick-event", this._onTickEvent);
  }

  /** 处理 tick-event — 逐条展示，当前事件高亮 / Handle tick-event, sequential with highlight */
  private _handleTickEvent(detail: {
    type: string;
    payload: Record<string, unknown>;
    phase?: "done";
  }): void {
    const displayTick = tickStore.getState().display_tick;
    if (displayTick !== this.currentTick || displayTick === 0) return;

    // done 阶段：取消高亮 / Done phase: remove highlight
    if (detail.phase === "done") {
      const active = this.listEl.querySelector(".event-active");
      if (active) active.classList.remove("event-active");
      return;
    }

    const ev: EventData = { type: detail.type, tick: displayTick, payload: detail.payload };

    // 移除空状态 / Remove empty state
    if (this.listEl.querySelector(".event-empty")) {
      this.listEl.innerHTML = "";
    }

    // 新事件：先取消上一行的 active，再追加新行并高亮 / New event: unhighlight previous, append and highlight new
    const prevActive = this.listEl.querySelector(".event-active");
    if (prevActive) prevActive.classList.remove("event-active");

    const line = this._createLine(ev);
    line.classList.add("event-active");
    const shouldScroll = this._shouldAutoScroll();
    this.listEl.appendChild(line);
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

  /** 销毁时移除 tick-event 监听 / Remove tick-event listener on destroy */
  destroy(): void {
    window.removeEventListener("tick-event", this._onTickEvent);
    super.destroy();
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
    pc_explore: "角色探索",
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
    case "pc_explore":
    case "character_explore": {
      const wp = payload.waypoints as Array<{ x: number; y: number }> | undefined;
      if (wp?.length) {
        return `(${payload.start_x},${payload.start_y}) → ${wp.map((p) => `(${p.x},${p.y})`).join(" → ")}`;
      }
      const fx = payload.final_x ?? payload.x ?? "?";
      const fy = payload.final_y ?? payload.y ?? "?";
      return `移动到 (${fx}, ${fy})`;
    }
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
