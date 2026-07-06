// --- / ---
/** DM 创造情境面板 — tick 开始时清空，dm_create 时逐字展开，带历史记录 */
import { Panel } from "./Panel";

/** tick 开始时清空，dm_create 时逐字展开，内嵌历史记录 / typewriter + inline history */
export class DMCreationPanel extends Panel {
  private contentEl!: HTMLElement; // 正文区 / Main content
  private historyEl!: HTMLElement; // 历史列表 / History list
  private typingTimer: ReturnType<typeof setInterval> | null = null;
  private displayedBrief = "";
  private targetBrief = "";
  private charIndex = 0;
  private history: string[] = []; // 历史记录缓存 / History cache
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
        <button class="panel-history-btn" id="dm-create-history-btn" title="情境历史">🕓</button>
      </div>
      <div class="panel-body dm-creation-body"></div>
      <div class="dm-history-overlay" id="dm-create-history-overlay" style="display:none">
        <div class="dm-history-header">
          <span>📜 DM 情境历史</span>
          <button id="dm-create-history-close" style="border:none;background:transparent;color:#ffd700;cursor:pointer;font-size:16px">✕</button>
        </div>
        <div class="dm-history-list"></div>
      </div>`;
    this.contentEl = el.querySelector(".dm-creation-body")!;
    this.historyEl = el.querySelector(".dm-history-list")!;
    el.querySelector("#dm-create-history-btn")!.addEventListener("click", () =>
      this._toggleHistory(el)
    );
    el.querySelector("#dm-create-history-close")!.addEventListener("click", () => {
      el.querySelector("#dm-create-history-overlay")!.setAttribute("style", "display:none");
    });
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
        this.history.push(this.targetBrief);
        return;
      }
      this.charIndex++;
      this.displayedBrief = this.targetBrief.slice(0, this.charIndex);
      this.contentEl.textContent = this.displayedBrief;
    }, 30);
  }

  private _toggleHistory(el: HTMLElement): void {
    const overlay = el.querySelector("#dm-create-history-overlay") as HTMLElement;
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

  destroy(): void {
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    if (this.typingTimer) clearInterval(this.typingTimer);
    super.destroy();
  }
}
