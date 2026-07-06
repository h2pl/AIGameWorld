/** 叙事面板 — 仅显示 DM 叙事、探索/交互记录，历史改为居中弹窗列表 */
import { Panel } from "./Panel";

const CHAR_MS = 40; // 逐字速度 / Per-char speed

/** tick 清空 + 逐字展开 + 居中弹窗历史 / clear on tick + typewriter + centered history overlay */
export class NarrativePanel extends Panel {
  private contentEl!: HTMLElement; // 正文区
  private history: string[] = []; // 历史缓存
  private _onTickStart: () => void;
  private _onTickEvent: (e: Event) => void;
  private _onKeydown: (e: KeyboardEvent) => void;

  constructor() {
    super("narrative-panel");
    this._onTickStart = () => this._clear();
    this._onTickEvent = (e: Event) => this._handle((e as CustomEvent).detail);
    this._onKeydown = (e) => {
      if (e.key === "Escape") this._hideHistory();
    };
  }

  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel narrative-panel";
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
    this.contentEl = el.querySelector(".narrative-body")!;
    el.querySelector("#narr-history-btn")!.addEventListener("click", () => this._showHistory());
    const overlay = el.querySelector("#narr-history-overlay") as HTMLElement;
    overlay.querySelector(".history-close")!.addEventListener("click", () => this._hideHistory());
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this._hideHistory();
    });
    return el;
  }

  protected bindStore(): void {
    window.addEventListener("tick-start", this._onTickStart);
    window.addEventListener("tick-event", this._onTickEvent);
  }

  protected bindEvents(): void {
    document.addEventListener("keydown", this._onKeydown);
  }

  private _clear(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.target = "";
    this.displayed = "";
    this.contentEl.innerHTML = "";
  }

  private timer: ReturnType<typeof setTimeout> | null = null;
  private displayed = "";
  private target = "";

  private _handle(detail: { type: string; payload: Record<string, unknown> }): void {
    // 叙事面板只展示 DM 叙事，不处理探索/交互等其他事件
    if (detail?.type !== "dm_narrative") return;
    const payload = detail.payload || {};
    const text = (payload.text as string) || (payload.narrative as string) || "";
    if (!text) return;
    if (this.target === text) return;

    this.target = text;
    this.displayed = "";
    this._reveal();
  }

  private _reveal(): void {
    if (!this.contentEl) return;
    const idx = this.displayed.length;
    if (idx >= this.target.length) {
      this.timer = null;
      this.history.push(this.target);
      return;
    }
    this.displayed = this.target.slice(0, idx + 1);
    this.contentEl.innerHTML = `<div class="narrative-line fade-in">${this._escape(this.displayed)}</div>`;
    this.contentEl.scrollTop = this.contentEl.scrollHeight;
    const delay = idx < 20 ? CHAR_MS : Math.max(15, CHAR_MS - (idx - 20) * 1.5);
    this.timer = setTimeout(() => this._reveal(), delay);
  }

  /** 打开叙事历史弹窗 / Open narrative history overlay */
  private _showHistory(): void {
    const overlay = this.el.querySelector("#narr-history-overlay") as HTMLElement;
    if (!overlay) return;
    const listEl = overlay.querySelector(".history-body") as HTMLElement;
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

  /** 关闭叙事历史弹窗 / Close narrative history overlay */
  private _hideHistory(): void {
    const overlay = this.el.querySelector("#narr-history-overlay") as HTMLElement;
    if (overlay) overlay.style.display = "none";
  }

  private _escape(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  destroy(): void {
    if (this.timer) clearTimeout(this.timer);
    document.removeEventListener("keydown", this._onKeydown);
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    super.destroy();
  }
}
