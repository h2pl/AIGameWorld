/** 历史事件面板 / History Event Panel — 半透明居中，展示全部历史事件 */
import { Panel } from "./Panel";
import type { EventData } from "../types";
import { CONFIG } from "../config";

const L = "[HistoryEventPanel]";

const EVENT_ICONS: Record<string, string> = {
  combat: "⚔️",
  dialogue: "🗣️",
  exploration: "🔍",
  quest: "📜",
  system: "⚙️",
};

export class HistoryEventPanel extends Panel {
  private listEl!: HTMLElement; // 事件列表容器 / Event list container
  private worldId: string; // 世界 ID / World ID
  private baseUrl: string; // 后端 API 地址 / Backend API base URL

  constructor(worldId: string) {
    super("history-event-panel");
    this.worldId = worldId;
    this.baseUrl = CONFIG.API.base;
  }

  // 构建半透明居中面板 DOM / Build semi-transparent centered panel DOM
  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "history-overlay";
    el.style.display = "none";
    el.innerHTML = `
      <div class="history-panel">
        <div class="history-header">
          <span class="history-title">📜 历史事件 / Event History</span>
          <button class="history-close" title="关闭">✕</button>
        </div>
        <div class="history-body"></div>
      </div>
    `;
    this.listEl = el.querySelector(".history-body")!;
    // 点击关闭按钮或遮罩关闭面板 / Close on button or overlay click
    el.querySelector(".history-close")!.addEventListener("click", () => this.hide());
    el.addEventListener("click", (e) => {
      if (e.target === el) this.hide();
    });
    return el;
  }

  // 绑定 ESC 关闭 / Bind ESC to close
  protected bindEvents(): void {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.el.style.display === "flex") {
        this.hide();
      }
    });
  }

  /** 打开并加载到指定 tick 为止的全部历史事件 */
  async open(currentTick: number): Promise<void> {
    this.el.style.display = "flex";
    this.listEl.innerHTML = `<div class="history-loading">加载中...</div>`;
    await this.loadHistory(currentTick);
  }

  // 隐藏面板 / Hide panel
  hide(): void {
    this.el.style.display = "none";
  }

  // 分页拉取历史事件 / Paginated fetch of historical events
  private async loadHistory(targetTick: number): Promise<void> {
    const events: EventData[] = [];
    let since = 0;
    try {
    while (since < targetTick) {
      const resp = await fetch(
        `${this.baseUrl}/api/world/${this.worldId}/events?since_tick=${since}`,
      );
      if (!resp.ok) break;
      const data = (await resp.json()) as { events: EventData[]; current_tick: number };
      if (data.events && data.events.length > 0) {
        events.push(...data.events);
        since = data.current_tick;
      } else {
        // 空窗期推进 since，避免死循环 / Advance since on empty window to avoid infinite loop
        if (data.current_tick <= since) break;
        since = data.current_tick;
      }
      if (since >= targetTick) break;
      await _sleep(50);
    }
    } catch (e) {
      console.warn(`${L} loadHistory failed`, e);
    }
    this._render(events);
  }

  // 渲染事件列表 / Render event list
  private _render(events: EventData[]): void {
    if (events.length === 0) {
      this.listEl.innerHTML = `<div class="history-empty">暂无历史事件</div>`;
      return;
    }

    // 按 tick 分组渲染 / Render grouped by tick
    const frag = document.createDocumentFragment();
    let lastTick = -1;
    for (const ev of events) {
      if (ev.tick !== lastTick) {
        lastTick = ev.tick || 0;
        const tickHeader = document.createElement("div");
        tickHeader.className = "history-tick-header";
        tickHeader.textContent = `— Tick ${lastTick} —`;
        frag.appendChild(tickHeader);
      }
      frag.appendChild(this._createLine(ev));
    }
    this.listEl.innerHTML = "";
    this.listEl.appendChild(frag);
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }

  // 创建单条事件 DOM / Create single event line
  private _createLine(ev: EventData): HTMLElement {
    const icon = EVENT_ICONS[ev.type] || "📌";
    const el = document.createElement("div");
    el.className = "history-line";
    el.innerHTML = `<span class="history-icon">${icon}</span><span class="history-text">${_readableType(
      ev.type,
    )}</span>`;
    el.title = ev.description || _readableType(ev.type);
    return el;
  }
}

// 事件类型中文名 / Readable event type names
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

// 延时辅助 / Sleep helper
function _sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
