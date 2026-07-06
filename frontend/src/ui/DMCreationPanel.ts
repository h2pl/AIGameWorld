/** DM 创造情境面板 — tick 开始时清空，dm_create 时逐字展开，历史改为居中弹窗列表 */
import { Panel } from "./Panel";

/** tick 开始时清空，dm_create 时逐字展开，居中弹窗历史 / typewriter + centered history overlay */
export class DMCreationPanel extends Panel {
  private contentEl!: HTMLElement; // 正文区 / Main content
  private typingTimer: ReturnType<typeof setInterval> | null = null;
  private displayedBrief = "";
  private targetBrief = "";
  private charIndex = 0;
  private history: string[] = []; // 历史记录缓存 / History cache
  private _onTickStart: () => void;
  private _onTickEvent: (e: Event) => void;
  private _onKeydown: (e: KeyboardEvent) => void;

  constructor() {
    super("dm-creation-panel");
    this._onTickStart = () => this._clear();
    this._onTickEvent = (e: Event) => this._handleTickEvent((e as CustomEvent).detail);
    this._onKeydown = (e) => {
      if (e.key === "Escape") this._hideHistory();
    };
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
      <div class="history-overlay" id="dm-create-history-overlay" style="display:none">
        <div class="history-panel">
          <div class="history-header">
            <span class="history-title">📜 DM 情境历史 / DM Context History</span>
            <button class="history-close" title="关闭">✕</button>
          </div>
          <div class="history-body"></div>
        </div>
      </div>`;
    this.contentEl = el.querySelector(".dm-creation-body")!;
    el.querySelector("#dm-create-history-btn")!.addEventListener("click", () =>
      this._showHistory()
    );
    const overlay = el.querySelector("#dm-create-history-overlay") as HTMLElement;
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

  /** 打开情境历史弹窗 / Open DM creation history overlay */
  private _showHistory(): void {
    const overlay = this.el.querySelector("#dm-create-history-overlay") as HTMLElement;
    if (!overlay) return;
    const listEl = overlay.querySelector(".history-body") as HTMLElement;
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

  /** 关闭情境历史弹窗 / Close DM creation history overlay */
  private _hideHistory(): void {
    const overlay = this.el.querySelector("#dm-create-history-overlay") as HTMLElement;
    if (overlay) overlay.style.display = "none";
  }

  private _escape(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  destroy(): void {
    document.removeEventListener("keydown", this._onKeydown);
    window.removeEventListener("tick-start", this._onTickStart);
    window.removeEventListener("tick-event", this._onTickEvent);
    if (this.typingTimer) clearInterval(this.typingTimer);
    super.destroy();
  }
}
