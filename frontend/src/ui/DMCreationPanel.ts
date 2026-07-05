/** DM 创造情境面板 / DM Creation Panel — 显示 plot_brief，带打字机渐入效果 */
import { Panel } from "./Panel";
import { tickStore, type TickState } from "../state/TickStore";

export class DMCreationPanel extends Panel {
  private contentEl!: HTMLElement;
  private typingTimer: ReturnType<typeof setTimeout> | null = null;
  private displayedBrief = "";
  private targetBrief = "";
  private charIndex = 0;

  constructor() {
    // 调用父类构建面板容器 / Call parent to build panel container
    super("dm-creation-panel");
  }

  /** 构建面板 DOM / Build panel DOM */
  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel dm-creation-panel";
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">🎲</span>
        <span class="panel-title">DM 创造情境</span>
      </div>
      <div class="panel-body dm-creation-body"></div>
    `;
    this.contentEl = el.querySelector(".dm-creation-body")!;
    return el;
  }

  /** 订阅 GameStore 状态变化 / Subscribe to GameStore changes */
  protected bindStore(): void {
    this.unsubscribe = tickStore.subscribe((s: TickState) => {
      this.onStateChange(s);
    });
  }

  /** 状态变更时触发新的打字机效果 / Trigger typewriter effect on state change */
  private onStateChange(state: TickState): void {
    if (!state.dm_plot_brief || state.dm_plot_brief === this.targetBrief) return;
    this.targetBrief = state.dm_plot_brief;
    this.charIndex = 0;
    this.displayedBrief = "";
    this.contentEl.innerHTML = "";
    if (this.typingTimer) {
      clearInterval(this.typingTimer);
      this.typingTimer = null;
    }
    this.startTyping();
  }

  /** 启动打字机渐入效果 / Start typewriter typing effect */
  private startTyping(): void {
    if (!this.targetBrief) return;
    this.typingTimer = window.setInterval(() => {
      if (this.charIndex >= this.targetBrief.length) {
        if (this.typingTimer) clearInterval(this.typingTimer);
        this.typingTimer = null;
        return;
      }
      this.charIndex++;
      this.displayedBrief = this.targetBrief.slice(0, this.charIndex);
      this.render();
    }, 30); // 每个字 30ms，约 33 字/秒
  }

  /** 渲染当前已显示的文本 / Render currently displayed text */
  private render(): void {
    this.contentEl.textContent = this.displayedBrief;
  }
}
