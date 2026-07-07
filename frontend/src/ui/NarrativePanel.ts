/** 叙事面板 — 固定大小，CSS fade-in 渐入显示 / Fixed size, fade-in on content */
import { Panel } from "./Panel";

/** fixed-size + fade-in + centered history overlay / 固定尺寸，渐入，居中弹窗历史 */
export class NarrativePanel extends Panel {
  /** 内容容器 / Content container */
  private contentEl!: HTMLElement;
  /** 叙事历史 / Narrative history */
  private history: string[] = [];
  /** 当前显示文本 / Currently displayed text */
  private currentText = "";
  /** fade-in 动画定时器 / Fade-in animation timer */
  private fadeTimer: ReturnType<typeof setTimeout> | null = null;
  /** tick 开始回调 / Tick start callback */
  private _onTickStart: () => void;
  /** tick 事件回调 / Tick event callback */
  private _onTickEvent: (e: Event) => void;
  /** 键盘事件回调 / Keyboard event callback */
  private _onKeydown: (e: KeyboardEvent) => void;

  constructor() {
    super("narrative-panel");
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
    el.className = "panel narrative-panel";
    // 面板主体 HTML / Panel body HTML
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">📖</span><span class="panel-title">叙事 / Narrative</span>
        <button class="panel-history-btn" id="narr-history-btn" title="叙事历史">🕓</button>
      </div>
      <div class="panel-body narrative-body"></div>
      <div class="history-overlay" id="narr-history-overlay" style="display:none">
        <div class="history-panel">
          <div class="history-header">
            <span class="history-title">📜 叙事历史 / Narrative History</span>
            <button class="history-close" title="关闭">✕</button>
          </div>
          <div class="history-body"></div>
        </div>
      </div>`;
    // 缓存内容容器 / Cache content container
    this.contentEl = el.querySelector(".narrative-body")!;
    // 历史按钮点击 / History button click
    el.querySelector("#narr-history-btn")!.addEventListener("click", () => this._showHistory());
    const overlay = el.querySelector("#narr-history-overlay") as HTMLElement;
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
    this.currentText = "";
    this.contentEl.innerHTML = `<span class="narrative-placeholder">等待叙事…</span>`;
  }

  /** 处理叙事事件 / Handle narrative event */
  private _handle(detail: { type: string; payload: Record<string, unknown> }): void {
    if (detail?.type !== "dm_narrative") return;
    const text = (detail.payload?.text as string) || (detail.payload?.narrative as string) || "";
    if (!text || text === this.currentText) return;

    this.currentText = text;

    if (this.fadeTimer) clearTimeout(this.fadeTimer);

    // 清空旧内容 / Clear old content
    this.contentEl.innerHTML = "";

    // 延迟一帧插入，让 CSS animation 重新触发 / Delay one frame for animation restart
    this.fadeTimer = setTimeout(() => {
      this.contentEl.innerHTML = `<div class="narrative-line fade-in">${this._escape(text)}</div>`;
      this.history.push(text);
      this.fadeTimer = null;
      this.contentEl.scrollTop = this.contentEl.scrollHeight;
      // 通知 NarrativeHandler 展示完成 / Signal complete for handler
      window.dispatchEvent(new CustomEvent("narrative-complete", { detail: { text } }));
    }, 50);
  }

  /** 显示历史弹层 / Show history overlay */
  private _showHistory(): void {
    const overlay = this.el.querySelector("#narr-history-overlay") as HTMLElement;
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
      : `<div class="history-empty">暂无叙事历史</div>`;
    overlay.style.display = "flex";
  }

  /** 隐藏历史弹层 / Hide history overlay */
  private _hideHistory(): void {
    const overlay = this.el.querySelector("#narr-history-overlay") as HTMLElement;
    if (overlay) overlay.style.display = "none";
  }

  /** HTML 转义 / HTML escape */
  private _escape(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /** 销毁面板，清理事件和定时器 / Destroy panel and clean up */
  destroy(): void {
    if (this.fadeTimer) clearTimeout(this.fadeTimer);
    document.removeEventListener("keydown", this._onKeydown);
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    super.destroy();
  }
}
