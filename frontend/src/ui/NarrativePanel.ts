// --- / ---
// -- file start -- / file start
/** 叙事面板 / Narrative Panel — dm_create 情节梗概 + dm_narrative 叙事文本，tick 开始时清空 */
import { Panel } from "./Panel";

const CHAR_MS = 40; // 逐字展开速度 / Per-character reveal speed

export class NarrativePanel extends Panel {
  private contentEl!: HTMLElement;
  private displayed = "";
  private target = "";
  private timer: ReturnType<typeof setTimeout> | null = null;
  private _onTickStart: (e: Event) => void;
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
        <button class="panel-history-btn" title="叙事历史">🕓</button>
      </div>
      <div class="panel-body narrative-body"></div>`;
    el.querySelector(".panel-history-btn")!.addEventListener("click", () =>
      window.dispatchEvent(new CustomEvent("show-event-history"))
    );
    this.contentEl = el.querySelector(".narrative-body")!;
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
    if (this.target === text) return; // 去重

    this.target = text;
    this.displayed = "";
    this._reveal();
  }

  /** 逐字展开 + 渐入 / Typewriter reveal with fade-in */
  private _reveal(): void {
    if (!this.contentEl) return;
    const idx = this.displayed.length;
    if (idx >= this.target.length) {
      this.timer = null;
      return;
    }
    this.displayed = this.target.slice(0, idx + 1);
    // 分包容器，每个字符独立渲染实现渐入
    this.contentEl.innerHTML = `<div class="narrative-line fade-in">${this._escape(this.displayed)}</div>`;
    this.contentEl.scrollTop = this.contentEl.scrollHeight;

    const delay = idx < 20 ? CHAR_MS : Math.max(15, CHAR_MS - (idx - 20) * 1.5);
    this.timer = setTimeout(() => this._reveal(), delay);
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
