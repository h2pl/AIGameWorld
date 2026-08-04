// -- file start -- / file start
/** 游戏 HUD / Game HUD — 场景名 + 等待提示 */
import Phaser from "phaser";
import { CONFIG } from "../config";
import { DEPTH } from "../constants";

export class GameHUD {
  private sceneNameText: Phaser.GameObjects.Text | null = null;
  private waitingText: Phaser.GameObjects.Text | null = null;

  constructor(private scene: Phaser.Scene) {}

  /** 创建 HUD / Create HUD */
  create(sceneName: string): void {
    this.sceneNameText = this.scene.add
      .text(8, 4, sceneName, {
        fontFamily: "Segoe UI, sans-serif",
        fontSize: "12px",
        color: "#ffd700",
        fontStyle: "bold",
        backgroundColor: "rgba(0,0,0,0.6)",
        padding: { x: 5, y: 2 },
      })
      .setScrollFactor(0)
      .setDepth(DEPTH.HUD);
  }

  /** 显示等待文本 / Show waiting text */
  showWaiting(text: string): void {
    this.waitingText = this.scene.add
      .text(CONFIG.CANVAS.width / 2, CONFIG.CANVAS.height / 2, text, {
        fontFamily: "Segoe UI, sans-serif",
        fontSize: "18px",
        color: "#ffd700",
      })
      .setOrigin(0.5)
      .setScrollFactor(0)
      .setDepth(DEPTH.HUD);
  }

  /** 隐藏等待文本 / Hide waiting text */
  hideWaiting(): void {
    if (this.waitingText) {
      this.waitingText.destroy();
      this.waitingText = null;
    }
  }

  /** 销毁 HUD / Destroy HUD */
  destroy(): void {
    if (this.sceneNameText) {
      this.sceneNameText.destroy();
      this.sceneNameText = null;
    }
    this.hideWaiting();
  }
}
