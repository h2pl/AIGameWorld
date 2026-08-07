/** 对话泡泡 / Dialogue bubble — 显示在角色头顶的临时气泡文本（纯 DOM 渲染，矢量清晰）
 *
 * 设计：
 * - 纯 DOM 元素，不通过 scene.add.dom（FIT 模式下 add.dom 内置定位对相机 zoom 处理不可靠，
 *   导致气泡偏离角色很远）。改为手动 worldToScreen 投影，每帧跟随相机 scroll/zoom/FIT。
 * - 人名放在内容前面，如 "Merchant: 晚上好"
 * - 泡泡宽度按文本自适应（CSS max-width 限制），高度自动延伸
 * - 单条对话完整显示，不再分页
 * - 用 HTML/CSS 渲染，与角色/事件面板一致的矢量字体，FIT 放大 canvas 不影响 DOM 文本清晰度。
 */

import Phaser from "phaser";
import { speedMs } from "../config/playback";
import { contentDuration } from "../utils/contentDuration";
import { worldToScreen, getOverlayHost } from "../utils/domProjection";

export type BubbleStyle = "dialogue" | "narration" | "thought";

export class DialogueBubble {
  private scene: Phaser.Scene;
  private pages: string[] = [];
  private pageIndex = 0;
  private timer?: number;
  private fadeTimer?: number;
  private onHide?: () => void;
  private style: BubbleStyle;
  private el!: HTMLElement;
  private textEl!: HTMLElement;
  private wx = 0;
  private wy = 0;
  private destroyed = false;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    text: string,
    speakerName?: string,
    onHide?: () => void,
    style: BubbleStyle = "dialogue"
  ) {
    this.scene = scene;
    this.wx = x;
    this.wy = y;
    this.style = style;
    this.onHide = onHide;

    const el = document.createElement("div");
    el.className = `dialogue-bubble dialogue-bubble--${style}`;
    el.style.position = "absolute";
    el.style.transform = "translate(-50%, -100%)"; // 底部中点对齐世界点
    el.style.pointerEvents = "auto";
    const textEl = document.createElement("div");
    textEl.className = "dialogue-bubble__text";
    el.appendChild(textEl);
    this.el = el;
    this.textEl = textEl;

    // 挂载到 #app 覆盖层 / Mount to overlay host
    getOverlayHost(scene).appendChild(el);

    // 初始隐藏，下一帧淡入（CSS transition 平滑）/ Start hidden, fade in next frame
    el.style.opacity = "0";
    requestAnimationFrame(() => {
      if (!this.destroyed) el.style.opacity = "1";
    });

    let fullText = speakerName?.trim() ? `${speakerName.trim()}: ${text}` : text;
    if (style === "thought") {
      fullText = `💡 ${fullText}`;
    } else if (style === "dialogue") {
      fullText = `🗣️ ${fullText}`;
    }
    this.pages = [fullText];

    el.addEventListener("click", () => this._skipOrAdvance());

    // 立即定位一帧 + 每帧跟随相机 / Position immediately + follow camera each frame
    this._sync();
    scene.events.on(Phaser.Scenes.Events.UPDATE, this._sync, this);

    this._showSegment(0);
  }

  /** 设置世界坐标 / Set world position */
  setWorldPosition(x: number, y: number): void {
    this.wx = x;
    this.wy = y;
    this._sync();
  }

  /** 每帧把世界坐标投影到屏幕 / Project world → screen each frame */
  private _sync(): void {
    if (this.destroyed) return;
    const p = worldToScreen(this.scene, this.wx, this.wy);
    this.el.style.left = `${p.x}px`;
    this.el.style.top = `${p.y}px`;
  }

  /** 显示第 i 段（淡入）/ Show segment i with fade-in */
  private _showSegment(i: number): void {
    this.pageIndex = i;
    this.textEl.textContent = this.pages[i];
    this.el.style.opacity = "0";
    requestAnimationFrame(() => {
      if (!this.destroyed) this.el.style.opacity = "1";
    });
    this.fadeTimer = window.setTimeout(() => this._scheduleAutoAdvance(), speedMs(300));
  }

  /** 渐出后翻到下一段；最后一段则关闭 / Fade out then advance or close */
  private _advance(): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    this.el.style.opacity = "0";
    window.setTimeout(() => {
      if (this.destroyed) return;
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
    this.el.style.opacity = "0";
    window.setTimeout(() => this.destroy(), speedMs(200));
  }

  /** 获取泡泡样式 / Get bubble style */
  getStyle(): BubbleStyle {
    return this.style;
  }

  /** 销毁 / Destroy */
  destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.scene.events.off(Phaser.Scenes.Events.UPDATE, this._sync, this);
    if (this.timer) window.clearTimeout(this.timer);
    if (this.fadeTimer) window.clearTimeout(this.fadeTimer);
    const cb = this.onHide;
    this.onHide = undefined;
    this.el.remove();
    cb?.();
  }
}
