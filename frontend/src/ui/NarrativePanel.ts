// --- / ---
/** 叙事面板 — dm/multi-type narration, typewriter reveal + inline history */
import { Panel } from "./Panel";

const CHAR_MS = 40; // 逐字速度 / Per-char speed

/** tick 清空 + 逐字展开 + 内嵌历史 / clear on tick + typewriter + history */
export class NarrativePanel extends Panel {
  private contentEl!: HTMLElement; // 正文区
  private historyEl!: HTMLElement; // 历史区
  private displayed = "";
  private target = "";
  private timer: ReturnType<typeof setTimeout> | null = null;
  private history: string[] = []; // 历史缓存
  private _onTickStart: () => void;
  private _onTickEvent: (e: Event) => void;

  constructor() {
    super("narrative-panel");
    this._onTickStart = () => this._clear();
    this._onTickEvent = (e: Event) => this._handle((e as CustomEvent).detail);
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
      <div class="dm-history-overlay" id="narr-history-overlay" style="display:none">
        <div class="dm-history-header">
          <span>📜 DM 叙事历史</span>
          <button id="narr-history-close" style="border:none;background:transparent;color:#ffd700;cursor:pointer;font-size:16px">✕</button>
        </div>
        <div class="dm-history-list"></div>
      </div>`;
    this.contentEl = el.querySelector(".narrative-body")!;
    this.historyEl = el.querySelector(".dm-history-list")!;
    el.querySelector("#narr-history-btn")!.addEventListener("click", () => this._toggleHistory(el));
    el.querySelector("#narr-history-close")!.addEventListener("click", () => {
      el.querySelector("#narr-history-overlay")!.setAttribute("style", "display:none");
    });
    return el;
  }

  protected bindStore(): void {
    window.addEventListener("tick-start", this._onTickStart);
    window.addEventListener("tick-event", this._onTickEvent);
  }

  private _clear(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.displayed = "";
    this.target = "";
    this.contentEl.innerHTML = "";
  }

  private _handle(detail: { type: string; payload: Record<string, unknown> }): void {
    if (!detail?.payload) return;
    let text = "";
    if (detail.type === "dm_create") {
      text = (detail.payload.plot_brief as string) || "";
    } else if (detail.type === "dm_narrative") {
      text = (detail.payload.text as string) || (detail.payload.narrative as string) || "";
    } else if (detail.type === "interact_narration" || detail.type === "explore_record") {
      text = (detail.payload.text as string) || "";
    }
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

  private _toggleHistory(el: HTMLElement): void {
    const overlay = el.querySelector("#narr-history-overlay") as HTMLElement;
    if (!overlay) return;
    const showing = overlay.style.display !== "none";
    if (showing) {
      overlay.style.display = "none";
      return;
    }
    this.historyEl.innerHTML = this.history.length
      ? this.history
          .map(
            (h, i) =>
              `<div class="history-line"><span class="history-tick">#${i + 1}</span> ${h}</div>`
          )
          .join("")
      : `<div class="history-empty">暂无历史</div>`;
    overlay.style.display = "block";
  }

  private _escape(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  destroy(): void {
    if (this.timer) clearTimeout(this.timer);
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    super.destroy();
  }
}
