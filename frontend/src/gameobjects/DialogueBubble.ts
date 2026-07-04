/** 对话泡泡 / Dialogue bubble — 显示在角色头顶的临时气泡文本
 *
 * 设计：
 * - 人名放在内容前面，如 "Merchant: 晚上好"
 * - 泡泡宽度随内容自适应，最长不超过 MAX_WIDTH
 * - 单条对话超过最大行数时，按页拆分成多个泡泡陆续显示
 */

import Phaser from "phaser";

const PADDING_X = 12;
const PADDING_Y = 8;
const MAX_WIDTH = 260;
const CORNER_RADIUS = 10;
const ARROW_HEIGHT = 8;
const MAX_LINES = 4;
const MIN_SHOW_MS = 1200;
const MAX_SHOW_MS = 5000;
const MS_PER_CHAR = 60;
const TEXT_FONT = "14px Segoe UI, Microsoft YaHei, sans-serif";
const TEXT_COLOR = "#1a1a1a";

export class DialogueBubble extends Phaser.GameObjects.Container {
  private bg!: Phaser.GameObjects.Graphics;
  private textObj!: Phaser.GameObjects.Text;
  private pages: string[] = [];
  private pageIndex = 0;
  private timer?: number;
  private onHide?: () => void;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    text: string,
    speakerName?: string,
    onHide?: () => void,
  ) {
    super(scene, x, y);
    this.onHide = onHide;
    scene.add.existing(this);
    // 泡泡在角色和 HUD 之上 / Bubble above characters and HUD
    this.setDepth(200);

    const fullText = speakerName?.trim()
      ? `${speakerName.trim()}: ${text}`
      : text;
    this.pages = this._splitPages(scene, fullText);

    this.textObj = scene.add.text(0, -ARROW_HEIGHT - PADDING_Y, "", {
      font: TEXT_FONT,
      color: TEXT_COLOR,
      wordWrap: { width: MAX_WIDTH - PADDING_X * 2 },
      align: "center",
    }).setOrigin(0.5, 1);

    this.bg = scene.add.graphics();
    this.add([this.bg, this.textObj]);

    this.setInteractive({ useHandCursor: true });
    this.on("pointerdown", () => this._advance());

    this.setAlpha(0);
    scene.tweens.add({ targets: this, alpha: 1, duration: 150 });

    this._showPage(0);
  }

  /** 显示第 i 页 / Show page i */
  private _showPage(i: number): void {
    this.pageIndex = i;
    this.textObj.setText(this.pages[i]);
    this._layout();
    this._scheduleAutoAdvance();
  }

  /** 绘制背景并调整交互区域 / Draw background and hit area */
  private _layout(): void {
    const bounds = this.textObj.getBounds();
    const w = Math.min(bounds.width + PADDING_X * 2, MAX_WIDTH);
    const h = bounds.height + PADDING_Y * 2;

    this.bg.clear();
    // 米白底色 / Cream background
    this.bg.fillStyle(0xfff8e7, 0.98);
    // 深棕边框 / Dark brown border
    this.bg.lineStyle(2, 0x5d4037, 0.9);
    this.bg.fillRoundedRect(-w / 2, -h - ARROW_HEIGHT, w, h, CORNER_RADIUS);
    this.bg.strokeRoundedRect(-w / 2, -h - ARROW_HEIGHT, w, h, CORNER_RADIUS);
    // 指向下方的三角 / Downward arrow
    this.bg.fillTriangle(0, 0, -6, -ARROW_HEIGHT, 6, -ARROW_HEIGHT);
    this.bg.lineBetween(-6, -ARROW_HEIGHT, 0, 0);
    this.bg.lineBetween(6, -ARROW_HEIGHT, 0, 0);

    this.setSize(w, h + ARROW_HEIGHT);
  }

  /** 翻到下一页；最后一页则关闭 / Advance to next page or close */
  private _advance(): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    if (this.pageIndex < this.pages.length - 1) {
      this._showPage(this.pageIndex + 1);
    } else {
      this.hide();
    }
  }

  /** 按文本长度计算当前页自动翻页/关闭时间 / Auto-advance duration by text length */
  private _scheduleAutoAdvance(): void {
    const text = this.pages[this.pageIndex];
    const showMs = Math.min(
      MAX_SHOW_MS,
      Math.max(MIN_SHOW_MS, MIN_SHOW_MS + text.length * MS_PER_CHAR),
    );
    this.timer = window.setTimeout(() => this._advance(), showMs);
  }

  /** 将长文本按最大行数拆成多页 / Split long text into pages */
  private _splitPages(scene: Phaser.Scene, fullText: string): string[] {
    const style: Phaser.Types.GameObjects.Text.TextStyle = {
      font: TEXT_FONT,
      color: TEXT_COLOR,
      wordWrap: { width: MAX_WIDTH - PADDING_X * 2 },
      align: "center",
    };

    // 用 MAX_LINES 行参考文本计算每页最大高度
    const ref = scene.add.text(0, 0, Array(MAX_LINES).fill("中").join("\n"), style)
      .setVisible(false);
    const maxHeight = ref.height;
    ref.destroy();

    const pages: string[] = [];
    let start = 0;
    while (start < fullText.length) {
      let lo = start + 1;
      let hi = fullText.length;
      let best = start + 1;
      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        const chunk = fullText.slice(start, mid);
        const temp = scene.add.text(0, 0, chunk, style).setVisible(false);
        const fits = temp.height <= maxHeight;
        temp.destroy();
        if (fits) {
          best = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }
      pages.push(fullText.slice(start, best));
      start = best;
    }
    return pages.length ? pages : [fullText];
  }

  /** 淡出并销毁 / Fade out and destroy */
  hide(): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    this.disableInteractive();
    this.scene.tweens.add({
      targets: this,
      alpha: 0,
      duration: 200,
      onComplete: () => this.destroy(),
    });
  }

  override destroy(fromScene?: boolean): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    const cb = this.onHide;
    this.onHide = undefined;
    super.destroy(fromScene);
    cb?.();
  }
}
