// -- file start -- / file start
/** 游戏 HUD / Game HUD — 场景名 + 等待提示（DOM 渲染，与角色/事件面板一致的矢量字体）/
 *  DOM overlay so text is crisp like the other panels (canvas Text is blurry under FIT upscaling). */
import Phaser from "phaser";
import { DEPTH } from "../constants";

export class GameHUD {
  private scene: Phaser.Scene;
  private container: HTMLElement;
  private sceneNameEl: HTMLElement | null = null;
  private waitingEl: HTMLElement | null = null;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.container = document.createElement("div");
    this.container.className = "game-hud";
    const parent = (scene.game.canvas?.parentElement as HTMLElement) ?? document.body;
    if (getComputedStyle(parent).position === "static") parent.style.position = "relative";
    parent.appendChild(this.container);
  }

  /** 创建 HUD / Create HUD */
  create(sceneName: string): void {
    this.sceneNameEl = document.createElement("div");
    this.sceneNameEl.className = "game-hud-scene";
    this.sceneNameEl.textContent = sceneName;
    this.container.appendChild(this.sceneNameEl);
  }

  /** 显示等待文本 / Show waiting text */
  showWaiting(text: string): void {
    this.hideWaiting();
    this.waitingEl = document.createElement("div");
    this.waitingEl.className = "game-hud-waiting";
    this.waitingEl.textContent = text;
    this.container.appendChild(this.waitingEl);
  }

  /** 隐藏等待文本 / Hide waiting text */
  hideWaiting(): void {
    if (this.waitingEl) {
      this.waitingEl.remove();
      this.waitingEl = null;
    }
  }

  /** 销毁 HUD / Destroy HUD */
  destroy(): void {
    this.sceneNameEl?.remove();
    this.sceneNameEl = null;
    this.hideWaiting();
    this.container.remove();
  }
}
