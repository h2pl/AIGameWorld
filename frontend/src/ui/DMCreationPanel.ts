/** DM 创造情境面板 — 固定大小，hints 即时显示，CSS fade-in 渐入 */
import { Panel } from "./Panel";

/** fixed-size + fade-in + hints always visible / 固定尺寸，渐入，hints 始终可见 */
export class DMCreationPanel extends Panel {
  /** 剧情梗概容器 / Plot brief container */
  private briefEl!: HTMLElement;
  /** 环境提示容器 / Hints container */
  private hintsEl!: HTMLElement;
  /** fade-in 动画定时器 / Fade-in animation timer */
  private fadeTimer: ReturnType<typeof setTimeout> | null = null;
  /** 当前剧情梗概 / Current plot brief */
  private currentBrief = "";
  /** 当前环境提示 / Current hints */
  private currentHints: string[] = [];
  /** 历史情境记录 / Historical context records */
  private history: string[] = [];
  /** tick 开始回调 / Tick start callback */
  private _onTickStart: () => void;
  /** tick 事件回调 / Tick event callback */
  private _onTickEvent: (e: Event) => void;
  /** 键盘事件回调 / Keyboard event callback */
  private _onKeydown: (e: KeyboardEvent) => void;

  constructor() {
    super("dm-creation-panel");
    // 绑定事件处理器 / Bind event handlers
    this._onTickStart = () => this._clear();
    this._onTickEvent = (e: Event) => this._handle((e as CustomEvent).detail);
    this._onKeydown = (e) => {
      if (e.key === "Escape") this._hideHistory();
    };
  }

  /** 构建面板 DOM / Build panel DOM */
  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel dm-creation-panel";
    el.dataset.testid = "dm-creation-panel";
    // 面板主体 HTML / Panel body HTML
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">🎲</span>
        <span class="panel-title">DM 创造情境</span>
        <button class="panel-history-btn" id="dm-create-history-btn" title="情境历史">🕓</button>
      </div>
      <div class="panel-body dm-creation-body" data-testid="dm-creation-body">
        <div class="dm-creation-brief" data-testid="dm-creation-brief"></div>
        <div class="dm-creation-hints" style="display:none" data-testid="dm-creation-hints"></div>
      </div>
      <div class="history-overlay" id="dm-create-history-overlay" style="display:none">
        <div class="history-panel">
          <div class="history-header">
            <span class="history-title">📜 DM 情境历史 / DM Context History</span>
            <button class="history-close" title="关闭">✕</button>
          </div>
          <div class="history-body"></div>
        </div>
      </div>`;
    // 缓存子元素引用 / Cache child element references
    this.briefEl = el.querySelector(".dm-creation-brief")!;
    this.hintsEl = el.querySelector(".dm-creation-hints")!;
    // 历史按钮点击 / History button click
    el.querySelector("#dm-create-history-btn")!.addEventListener("click", () =>
      this._showHistory()
    );
    const overlay = el.querySelector("#dm-create-history-overlay") as HTMLElement;
    overlay.querySelector(".history-close")!.addEventListener("click", () => this._hideHistory());
    // 点击遮罩关闭历史 / Close history when clicking overlay
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this._hideHistory();
    });
    return el;
  }

  /** 绑定 store 相关事件 / Bind store-related events */
  protected bindStore(): void {
    window.addEventListener("tick-start", this._onTickStart);
    window.addEventListener("tick-event", this._onTickEvent);
  }

  /** 绑定 DOM 事件 / Bind DOM events */
  protected bindEvents(): void {
    document.addEventListener("keydown", this._onKeydown);
  }

  /** 清空面板内容 / Clear panel content */
  private _clear(): void {
    if (this.fadeTimer) {
      clearTimeout(this.fadeTimer);
      this.fadeTimer = null;
    }
    this.currentBrief = "";
    this.currentHints = [];
    this.briefEl.innerHTML = `<span class="dm-placeholder">等待 DM 情境…</span>`;
    this.hintsEl.style.display = "none";
  }

  /** 处理 tick 事件 / Handle tick event */
  private _handle(detail: { type: string; payload: Record<string, unknown> }): void {
    if (detail.type !== "dm_create") return;
    const brief = (detail.payload?.plot_brief as string) || "";
    const hints = Array.isArray(detail.payload?.hints) ? (detail.payload?.hints as string[]) : [];

    // 内容未变则跳过 / Skip if unchanged
    if (brief === this.currentBrief && hints.length === this.currentHints.length) return;

    this.currentBrief = brief;
    this.currentHints = hints;

    if (this.fadeTimer) clearTimeout(this.fadeTimer);

    // 先清空旧内容，触发重新 fade-in / Clear old content, trigger re-fade
    this.briefEl.innerHTML = "";
    this.hintsEl.style.display = "none";

    // 延迟一帧后插入新内容，让 CSS animation 重新触发 / Insert after a frame for animation restart
    this.fadeTimer = setTimeout(() => {
      if (brief) {
        this.briefEl.innerHTML = `<div class="dm-creation-line fade-in">${this._escape(brief)}</div>`;
        this.history.push(brief);
      }
      this._renderHints(hints);
      this.fadeTimer = null;
    }, 50);
  }

  /** 渲染环境提示 / Render hints */
  private _renderHints(hints: string[]): void {
    if (!hints.length) {
      this.hintsEl.style.display = "none";
      return;
    }
    this.hintsEl.innerHTML =
      `<div class="dm-hints-title">环境提示 / Hints</div>` +
      `<ul class="dm-hints-list">${hints.map((h, i) => `<li class="dm-hint-item fade-in" style="animation-delay:${i * 0.15}s">${this._escape(h)}</li>`).join("")}</ul>`;
    this.hintsEl.style.display = "block";
  }

  /** 显示历史弹层 / Show history overlay */
  private _showHistory(): void {
    const overlay = this.el.querySelector("#dm-create-history-overlay") as HTMLElement;
    if (!overlay) return;
    const listEl = overlay.querySelector(".history-body") as HTMLElement;
    // 渲染历史列表 / Render history list
    listEl.innerHTML = this.history.length
      ? this.history
          .map(
            (h, i) =>
              `<div class="history-line"><span class="history-tick">#${i + 1}</span><span class="history-text">${this._escape(h)}</span></div>`
          )
          .join("")
      : `<div class="history-empty">暂无 DM 情境历史</div>`;
    overlay.style.display = "flex";
  }

  /** 隐藏历史弹层 / Hide history overlay */
  private _hideHistory(): void {
    const overlay = this.el.querySelector("#dm-create-history-overlay") as HTMLElement;
    if (overlay) overlay.style.display = "none";
  }

  /** HTML 转义 / HTML escape */
  private _escape(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /** 销毁面板，清理事件和定时器 / Destroy panel and clean up */
  destroy(): void {
    document.removeEventListener("keydown", this._onKeydown);
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    if (this.fadeTimer) clearTimeout(this.fadeTimer);
    super.destroy();
  }
}
