/** 对话泡泡 / Dialogue bubble — 显示在角色头顶的临时气泡文本（DOM 渲染，矢量清晰）
 *
 * 设计：
 * - 人名放在内容前面，如 "Merchant: 晚上好"
 * - 泡泡宽度按文本自适应（CSS max-width 限制），高度自动延伸
 * - 单条对话完整显示，不再分页
 * - 用 HTML/CSS 渲染（scene.add.dom），与角色/事件面板一致的矢量字体，
 *   FIT 放大 canvas 不影响 DOM 文本清晰度（canvas 内 Text 位图放大即糊）。
 */

import Phaser from "phaser";
import { speedMs } from "../config/playback";
import { contentDuration } from "../utils/contentDuration";

export type BubbleStyle = "dialogue" | "narration" | "thought";

export class DialogueBubble extends Phaser.GameObjects.DOMElement {
  private pages: string[] = [];
  private pageIndex = 0;
  private timer?: number;
  private fadeTimer?: number;
  private onHide?: () => void;
  private style: BubbleStyle;
  private textEl!: HTMLElement;
  private bubbleEl!: HTMLElement;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    text: string,
    speakerName?: string,
    onHide?: () => void,
    style: BubbleStyle = "dialogue"
  ) {
    const bubbleEl = document.createElement("div");
    bubbleEl.className = `dialogue-bubble dialogue-bubble--${style}`;
    const textEl = document.createElement("div");
    textEl.className = "dialogue-bubble__text";
    bubbleEl.appendChild(textEl);

    super(scene, x, y, bubbleEl);
    this.style = style;
    this.onHide = onHide;
    this.bubbleEl = bubbleEl;
    this.textEl = textEl;
    scene.add.existing(this);
    this.setDepth(200);
    // 泡泡底部中点对齐角色头顶 / Bottom-center anchored above the character
    this.setOrigin(0.5, 1);

    let fullText = speakerName?.trim() ? `${speakerName.trim()}: ${text}` : text;
    if (style === "thought") {
      fullText = `💡 ${fullText}`;
    } else if (style === "dialogue") {
      fullText = `🗣️ ${fullText}`;
    }
    this.pages = [fullText];

    // 初始隐藏，下一帧淡入（CSS transition 平滑）/
    // Start hidden, fade in next frame via CSS transition
    this.setAlpha(0);
    requestAnimationFrame(() => this.setAlpha(1));

    this._showSegment(0);

    bubbleEl.addEventListener("click", () => this._skipOrAdvance());
  }

  /** 显示第 i 段（淡入）/ Show segment i with fade-in */
  private _showSegment(i: number): void {
    this.pageIndex = i;
    this.textEl.textContent = this.pages[i];
    this.setAlpha(0);
    requestAnimationFrame(() => this.setAlpha(1));
    this.fadeTimer = window.setTimeout(() => this._scheduleAutoAdvance(), speedMs(300));
  }

  /** 渐出后翻到下一段；最后一段则关闭 / Fade out then advance or close */
  private _advance(): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    this.setAlpha(0);
    window.setTimeout(() => {
      if (this.pageIndex < this.pages.length - 1) {
        this._showSegment(this.pageIndex + 1);
      } else {
        this.hide();
      }
    }, speedMs(200));
  }

  /** 点击跳过：如有定时器立即前进，否则正常渐出 / Click to skip */
  private _skipOrAdvance(): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    this._advance();
  }

  /** 按文本长度计算当前页自动翻页/关闭时间 / Auto-advance duration by text length */
  private _scheduleAutoAdvance(): void {
    const text = this.pages[this.pageIndex];
    let showMs: number;
    if (this.style === "narration") {
      showMs = Math.max(speedMs(contentDuration(text)), speedMs(1000));
    } else {
      const minMs = speedMs(1000);
      const perChar = speedMs(40);
      const maxMs = speedMs(4000);
      showMs = Math.min(maxMs, Math.max(minMs, minMs + text.length * perChar));
    }
    this.timer = window.setTimeout(() => this._advance(), showMs);
  }

  /** 淡出并销毁 / Fade out and destroy */
  hide(): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    this.setAlpha(0);
    window.setTimeout(() => this.destroy(), speedMs(200));
  }

  /** 获取泡泡样式 / Get bubble style */
  getStyle(): BubbleStyle {
    return this.style;
  }

  override destroy(fromScene?: boolean): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    if (this.fadeTimer) {
      window.clearTimeout(this.fadeTimer);
      this.fadeTimer = undefined;
    }
    const cb = this.onHide;
    this.onHide = undefined;
    super.destroy(fromScene);
    cb?.();
  }
}
