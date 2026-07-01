/** 叙事面板 / Narrative Panel — 展示 DM 生成的叙事文本，自动滚动 */
import { Panel } from "./Panel";
import { gameStore, type GameState } from "../state/GameStore";

export class NarrativePanel extends Panel {
  private contentEl!: HTMLElement;
  private lines: string[] = [];
  private $max = 200; // 最多保留 200 行 / Max lines

  constructor() {
    super("narrative-panel");
  }

  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel narrative-panel";
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">📜</span>
        <span class="panel-title">叙事 / Narrative</span>
      </div>
      <div class="panel-body narrative-body"></div>
    `;
    this.contentEl = el.querySelector(".narrative-body")!;
    return el;
  }

  protected bindStore(): void {
    this.unsubscribe = gameStore.subscribe((s: GameState) => {
      this.onStateChange(s);
    });
  }

  private onStateChange(state: GameState): void {
    if (!state.narrative) return;
    // 避免重复追加同一行 / Avoid duplicating same line
    if (this.lines.length > 0 && this.lines[this.lines.length - 1] === state.narrative) return;
    this.lines.push(state.narrative);
    if (this.lines.length > this.$max) this.lines.shift();
    this.render();
  }

  private render(): void {
    this.contentEl.innerHTML = this.lines
      .map((l, i) => `<div class="narrative-line">${this.escapeHtml(l)}</div>`)
      .join("");
    this.contentEl.scrollTop = this.contentEl.scrollHeight;
  }

  private escapeHtml(s: string): string {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }
}
