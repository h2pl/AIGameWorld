// --- / ---
// -- file start -- / file start
/** DM 创造情境面板 / DM Creation Panel — 通过 window tick-event 消费 dm_create */
import { Panel } from "./Panel";

export class DMCreationPanel extends Panel {
  private contentEl!: HTMLElement;
  private typingTimer: ReturnType<typeof setInterval> | null = null;
  private displayedBrief = "";
  private targetBrief = "";
  private charIndex = 0;
  private _onTickEvent: (e: Event) => void;

  constructor() {
    super("dm-creation-panel");
    this._onTickEvent = (e: Event) => this._handleTickEvent((e as CustomEvent).detail);
  }

  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel dm-creation-panel";
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">🎲</span>
        <span class="panel-title">DM 创造情境</span>
      </div>
      <div class="panel-body dm-creation-body"></div>`;
    this.contentEl = el.querySelector(".dm-creation-body")!;
    return el;
  }

  protected bindStore(): void {
    window.addEventListener("tick-event", this._onTickEvent);
  }

  private _handleTickEvent(detail: { type: string; payload: Record<string, unknown> }): void {
    if (detail.type !== "dm_create") return;
    const brief = (detail.payload?.plot_brief as string) || "";
    if (!brief || brief === this.targetBrief) return;
    this.targetBrief = brief;
    this.charIndex = 0;
    this.displayedBrief = "";
    this.contentEl.innerHTML = "";
    if (this.typingTimer) { clearInterval(this.typingTimer); this.typingTimer = null; }
    this._startTyping();
  }

  private _startTyping(): void {
    this.typingTimer = setInterval(() => {
      if (this.charIndex >= this.targetBrief.length) {
        if (this.typingTimer) { clearInterval(this.typingTimer); this.typingTimer = null; }
        return;
      }
      this.charIndex++;
      this.displayedBrief = this.targetBrief.slice(0, this.charIndex);
      this.contentEl.textContent = this.displayedBrief;
    }, 30);
  }

  destroy(): void {
    window.removeEventListener("tick-event", this._onTickEvent);
    if (this.typingTimer) clearInterval(this.typingTimer);
    super.destroy();
  }
}
