/** 历史事件面板 / History Event Panel — 半透明居中，分页展示全部历史事件 */
import { Panel } from "./Panel";
import type { EventData } from "../types";
import { CONFIG } from "../config";

const L = "[HistoryEventPanel]";
const PAGE_TICK_LIMIT = 5; // 每页 tick 数量 / Ticks per page

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

export class HistoryEventPanel extends Panel {
  private listEl!: HTMLElement; // 事件列表容器 / Event list container
  private footerEl!: HTMLElement; // 分页控件容器 / Pagination footer
  private pageInput!: HTMLInputElement; // 页码输入框 / Page input
  private pageInfo!: HTMLElement; // 页码信息 / Page info
  private worldId: string; // 世界 ID / World ID
  private baseUrl: string; // 后端 API 地址 / Backend API base URL
  private targetTick = 0; // 目标加载到的最大 tick / Target max tick
  private currentPage = 1; // 当前页码（从 1 开始）/ Current page number
  private totalPages = 1; // 总页数 / Total pages

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
        <div class="history-footer"></div>
      </div>
    `;
    this.listEl = el.querySelector(".history-body")!;
    this.footerEl = el.querySelector(".history-footer")!;
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

  /** 打开并加载历史事件 */
  async open(currentTick: number): Promise<void> {
    this.el.style.display = "flex";
    this.targetTick = currentTick;
    this.totalPages = Math.max(1, Math.ceil(this.targetTick / PAGE_TICK_LIMIT));
    this.currentPage = 1;
    this._buildPagination();
    await this._loadPage(this.currentPage);
  }

  // 隐藏面板 / Hide panel
  hide(): void {
    this.el.style.display = "none";
  }

  // 构建分页控件 / Build pagination controls
  private _buildPagination(): void {
    this.footerEl.innerHTML = "";
    this.footerEl.style.cssText = "display:flex;align-items:center;justify-content:center;gap:8px;padding:10px;border-top:1px solid rgba(255,215,0,0.2);";

    const btnPrev = document.createElement("button");
    btnPrev.textContent = "上一页";
    btnPrev.style.cssText = "padding:4px 10px;border-radius:4px;border:none;background:#555;color:#fff;cursor:pointer;";
    btnPrev.addEventListener("click", () => this._goToPage(this.currentPage - 1));

    const btnNext = document.createElement("button");
    btnNext.textContent = "下一页";
    btnNext.style.cssText = "padding:4px 10px;border-radius:4px;border:none;background:#555;color:#fff;cursor:pointer;";
    btnNext.addEventListener("click", () => this._goToPage(this.currentPage + 1));

    this.pageInfo = document.createElement("span");
    this.pageInfo.style.cssText = "color:#ffd700;font-size:13px;min-width:70px;text-align:center;";

    this.pageInput = document.createElement("input");
    this.pageInput.type = "number";
    this.pageInput.min = "1";
    this.pageInput.max = String(this.totalPages);
    this.pageInput.value = "1";
    this.pageInput.style.cssText = "width:50px;text-align:center;border-radius:4px;border:1px solid #555;background:#222;color:#fff;";
    this.pageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const page = parseInt(this.pageInput.value, 10);
        if (!isNaN(page)) this._goToPage(page);
      }
    });

    const btnJump = document.createElement("button");
    btnJump.textContent = "跳转";
    btnJump.style.cssText = "padding:4px 10px;border-radius:4px;border:none;background:#3498db;color:#fff;cursor:pointer;";
    btnJump.addEventListener("click", () => {
      const page = parseInt(this.pageInput.value, 10);
      if (!isNaN(page)) this._goToPage(page);
    });

    this.footerEl.appendChild(btnPrev);
    this.footerEl.appendChild(this.pageInfo);
    this.footerEl.appendChild(btnNext);
    this.footerEl.appendChild(this.pageInput);
    this.footerEl.appendChild(btnJump);
    this._updatePageInfo();
  }

  // 跳转到指定页 / Go to specific page
  private async _goToPage(page: number): Promise<void> {
    if (page < 1 || page > this.totalPages) return;
    this.currentPage = page;
    this.pageInput.value = String(page);
    this._updatePageInfo();
    await this._loadPage(page);
  }

  // 更新页码显示 / Update page info display
  private _updatePageInfo(): void {
    this.pageInfo.textContent = `第 ${this.currentPage} / ${this.totalPages} 页`;
  }

  // 加载指定页 / Load specific page
  private async _loadPage(page: number): Promise<void> {
    const sinceTick = (page - 1) * PAGE_TICK_LIMIT;
    const endTick = Math.min(page * PAGE_TICK_LIMIT, this.targetTick);
    this.listEl.innerHTML = `<div class="history-loading">加载中...</div>`;

    try {
      const resp = await fetch(
        `${this.baseUrl}/api/world/${this.worldId}/events?since_tick=${sinceTick}&tick_limit=${PAGE_TICK_LIMIT}`,
      );
      if (!resp.ok) {
        this.listEl.innerHTML = `<div class="history-empty">加载失败</div>`;
        return;
      }
      const data = (await resp.json()) as { events: EventData[]; display_tick: number };
      this._render(data.events || [], sinceTick + 1, endTick);
    } catch (e) {
      console.warn(`${L} _loadPage failed`, e);
      this.listEl.innerHTML = `<div class="history-empty">加载失败</div>`;
    }
  }

  // 渲染事件列表 / Render event list
  private _render(events: EventData[], startTick: number, endTick: number): void {
    if (events.length === 0) {
      this.listEl.innerHTML = `<div class="history-empty">暂无历史事件</div>`;
      return;
    }

    const frag = document.createDocumentFragment();
    let lastTick = -1;
    for (const ev of events) {
      const tick = ev.tick || 0;
      // 过滤掉不在当前页范围内的事件 / Filter events outside current page range
      if (tick < startTick || tick > endTick) continue;
      if (tick !== lastTick) {
        lastTick = tick;
        const tickHeader = document.createElement("div");
        tickHeader.className = "history-tick-header";
        tickHeader.textContent = `— Tick ${lastTick} —`;
        frag.appendChild(tickHeader);
      }
      frag.appendChild(this._createLine(ev));
    }
    this.listEl.innerHTML = "";
    this.listEl.appendChild(frag);
    this.listEl.scrollTop = 0;
  }

  // 创建单条事件 DOM — 与事件列表面板保持完全一致
  private _createLine(ev: EventData): HTMLElement {
    const icon = EVENT_ICONS[ev.type] || "📌";
    const typeLabel = _readableType(ev.type);
    const content = _formatPayload(ev);
    const el = document.createElement("div");
    el.className = "history-line";
    el.innerHTML = `<span class="history-icon">${icon}</span><span class="history-type">${typeLabel}</span><span class="history-content">${content}</span>`;
    return el;
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

/** 格式化 payload 为可读文本 — 与事件列表面板保持完全一致 */
function _formatPayload(ev: EventData): string {
  const payload = ev.payload || {};

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
    default:
      return JSON.stringify(payload).slice(0, 500);
  }
}
