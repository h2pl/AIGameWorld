/** 对话泡泡 / Dialogue bubble — 显示在角色头顶的临时气泡文本 */

import Phaser from "phaser";

const PADDING_X = 12;
const PADDING_Y = 10;
const MAX_WIDTH = 220;
const CORNER_RADIUS = 10;
const ARROW_HEIGHT = 10;
const MIN_SHOW_MS = 3500;
const MAX_SHOW_MS = 9000;
const MS_PER_CHAR = 70;
const NAME_FONT = "bold 11px Segoe UI, Microsoft YaHei, sans-serif";
const TEXT_FONT = "14px Segoe UI, Microsoft YaHei, sans-serif";

export class DialogueBubble extends Phaser.GameObjects.Container {
  private bg!: Phaser.GameObjects.Graphics;
  private textObj!: Phaser.GameObjects.Text;
  private nameObj?: Phaser.GameObjects.Text;
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

    const name = speakerName?.trim();
    let nameHeight = 0;
    if (name) {
      this.nameObj = scene.add.text(0, -ARROW_HEIGHT - PADDING_Y, name, {
        font: NAME_FONT,
        color: "#8b4513",
      }).setOrigin(0.5, 1);
      nameHeight = this.nameObj.height + 2;
    }

    this.textObj = scene.add.text(0, -ARROW_HEIGHT - PADDING_Y - nameHeight, text, {
      font: TEXT_FONT,
      color: "#1a1a1a",
      wordWrap: { width: MAX_WIDTH - PADDING_X * 2 },
      align: "center",
    }).setOrigin(0.5, 1);

    this.bg = scene.add.graphics();
    this.drawBackground();

    const children: Phaser.GameObjects.GameObject[] = [this.bg];
    if (this.nameObj) children.push(this.nameObj);
    children.push(this.textObj);
    this.add(children);

    this.setAlpha(0);
    scene.tweens.add({ targets: this, alpha: 1, duration: 200 });

    // 根据文本长度自适应显示时长 / Adaptive duration by text length
    const showMs = Math.min(MAX_SHOW_MS, Math.max(MIN_SHOW_MS, MIN_SHOW_MS + text.length * MS_PER_CHAR));
    this.timer = window.setTimeout(() => this.hide(), showMs);

    // 点击泡泡可提前关闭 / Click bubble to close early
    this.setSize(MAX_WIDTH, this.textObj.height + nameHeight + PADDING_Y * 2 + ARROW_HEIGHT);
    this.setInteractive({ useHandCursor: true });
    this.on("pointerdown", () => this.hide());
  }

  /** 绘制圆角泡泡背景与小三角 / Draw rounded bubble background and arrow */
  private drawBackground(): void {
    const textBounds = this.textObj.getBounds();
    const nameBounds = this.nameObj?.getBounds();
    const contentW = Math.max(textBounds.width, nameBounds ? nameBounds.width : 0);
    const w = Math.min(contentW + PADDING_X * 2, MAX_WIDTH);
    const h = textBounds.height + (nameBounds ? nameBounds.height + 2 : 0) + PADDING_Y * 2;
    this.bg.clear();
    // 米白底色 / Cream background
    this.bg.fillStyle(0xfff8e7, 0.98);
    // 深棕边框 / Dark brown border
    this.bg.lineStyle(2, 0x5d4037, 0.9);
    this.bg.fillRoundedRect(-w / 2, -h - ARROW_HEIGHT, w, h, CORNER_RADIUS);
    this.bg.strokeRoundedRect(-w / 2, -h - ARROW_HEIGHT, w, h, CORNER_RADIUS);
    // 指向下方的三角 / Downward arrow
    this.bg.fillTriangle(0, 0, -7, -ARROW_HEIGHT, 7, -ARROW_HEIGHT);
    this.bg.lineBetween(-7, -ARROW_HEIGHT, 0, 0);
    this.bg.lineBetween(7, -ARROW_HEIGHT, 0, 0);
  }

  /** 淡出并销毁 / Fade out and destroy */
  hide(): void {
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
    // 避免重复触发 / Avoid duplicate triggers
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
