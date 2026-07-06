// --- / ---
// -- file start -- / file start
/** DM 创造情境面板 / DM Creation Panel — tick 开始时清空，dm_create 时逐字展开 */
import { Panel } from "./Panel";

export class DMCreationPanel extends Panel {
  private contentEl!: HTMLElement;
  private typingTimer: ReturnType<typeof setInterval> | null = null;
  private displayedBrief = "";
  private targetBrief = "";
  private charIndex = 0;
  private _onTickStart: () => void;
  private _onTickEvent: (e: Event) => void;

  constructor() {
    super("dm-creation-panel");
    this._onTickStart = () => this._clear();
    this._onTickEvent = (e: Event) => this._handleTickEvent((e as CustomEvent).detail);
  }

  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel dm-creation-panel";
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">🎲</span>
        <span class="panel-title">DM 创造情境</span>
        <button class="panel-history-btn dm-history-btn" title="情境历史">🕓</button>
      </div>
      <div class="panel-body dm-creation-body"></div>`;
    el.querySelector(".dm-history-btn")!.addEventListener("click", () =>
      window.dispatchEvent(new CustomEvent("show-event-history"))
    );
    this.contentEl = el.querySelector(".dm-creation-body")!;
    return el;
  }

  protected bindStore(): void {
    window.addEventListener("tick-start", this._onTickStart);
    window.addEventListener("tick-event", this._onTickEvent);
  }

  private _clear(): void {
    if (this.typingTimer) {
      clearInterval(this.typingTimer);
      this.typingTimer = null;
    }
    this.targetBrief = "";
    this.displayedBrief = "";
    this.charIndex = 0;
    this.contentEl.innerHTML = "";
  }

  private _handleTickEvent(detail: { type: string; payload: Record<string, unknown> }): void {
    if (detail.type !== "dm_create") return;
    const brief = (detail.payload?.plot_brief as string) || "";
    if (!brief || brief === this.targetBrief) return;
    this._clear();
    this.targetBrief = brief;
    this._startTyping();
  }

  /** 逐字打字动画 / Typewriter animation */
  private _startTyping(): void {
    this.typingTimer = setInterval(() => {
      if (this.charIndex >= this.targetBrief.length) {
        if (this.typingTimer) {
          clearInterval(this.typingTimer);
          this.typingTimer = null;
        }
        return;
      }
      this.charIndex++;
      this.displayedBrief = this.targetBrief.slice(0, this.charIndex);
      this.contentEl.textContent = this.displayedBrief;
    }, 30);
  }

  destroy(): void {
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    if (this.typingTimer) clearInterval(this.typingTimer);
    super.destroy();
  }
}
