// --- / ---
// -- file start -- / file start
/** 叙事面板 / Narrative Panel — 通过 window tick-event 消费 dm_narrative */
import { Panel } from "./Panel";

export class NarrativePanel extends Panel {
  private contentEl!: HTMLElement;
  private lines: string[] = [];
  private _onTickEvent: (e: Event) => void;

  constructor() {
    super("narrative-panel");
    this._onTickEvent = (e: Event) => this._handleTickEvent((e as CustomEvent).detail);
  }

  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel narrative-panel";
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">📖</span><span class="panel-title">叙事 / Narrative</span>
      </div>
      <div class="panel-body narrative-body"></div>`;
    this.contentEl = el.querySelector(".narrative-body")!;
    return el;
  }

  protected bindStore(): void {
    window.addEventListener("tick-event", this._onTickEvent);
  }

  private _handleTickEvent(detail: { type: string; payload: Record<string, unknown> }): void {
    if (detail.type !== "dm_narrative") return;
    const text = (detail.payload?.text as string) || (detail.payload?.narrative as string);
    if (!text) return;
    if (this.lines.length > 0 && this.lines[this.lines.length - 1] === text) return;
    this.lines.push(text);
    this._render();
  }

  private _render(): void {
    this.contentEl.innerHTML = this.lines
      .map(l => `<div class="narrative-line">${this._escape(l)}</div>`)
      .join("");
    this.contentEl.scrollTop = this.contentEl.scrollHeight;
  }

  private _escape(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  destroy(): void {
    window.removeEventListener("tick-event", this._onTickEvent);
    super.destroy();
  }
}
