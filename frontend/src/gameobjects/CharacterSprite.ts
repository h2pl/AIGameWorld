/** 角色精灵 / Character Sprite — 世界坐标 + 名字标签 + 血条 + 点击 */

import Phaser from "phaser";
import { DialogueBubble } from "./DialogueBubble";
import type { CharacterData } from "../types";
import { playState } from "../utils/playState";
import { speedMs } from "../config/playback";

export class CharacterSprite {
  readonly id: string;
  readonly data: CharacterData;
  private scene: Phaser.Scene;
  private sprite: Phaser.GameObjects.Sprite; // 主精灵 / Main sprite
  private nameTag: Phaser.GameObjects.DOMElement; // 名字标签(DOM,矢量清晰) / Name label (DOM)
  private hpBar: Phaser.GameObjects.Graphics; // 血条 / HP bar
  private ring: Phaser.GameObjects.Graphics | null = null; // PC 金环 / Gold ring
  private bubble: DialogueBubble | null = null; // 当前对话泡泡 / Current dialogue bubble
  private tileSize = 32;
  private thinkCount = 0; // 决策泡泡触发次数 / Decision bubble trigger count for E2E

  constructor(scene: Phaser.Scene, data: CharacterData, wx: number, wy: number, tileSize: number) {
    this.scene = scene;
    this.data = data;
    this.id = data.id;
    this.tileSize = tileSize;

    // 纹理 / Texture
    const key = scene.textures.exists(data.id) ? data.id : data.is_pc ? "fighter_fb" : "actor_fb";
    this.sprite = scene.add
      .sprite(wx, wy, key)
      .setOrigin(0.5, 0.5)
      .setInteractive({ useHandCursor: true });

    // PC 金环 / Gold ring for PC
    if (data.is_pc) {
      this.ring = scene.add.graphics();
      this.ring.lineStyle(2, 0xffd700, 0.8);
      this.ring.strokeCircle(wx, wy, tileSize * 0.35);
    }

    // 名字（DOM 渲染，矢量清晰，与面板一致；FIT 放大 canvas 不影响 DOM 文本）/
    // Name as DOM so it stays crisp under FIT upscaling (unlike canvas Text).
    const nameEl = document.createElement("div");
    nameEl.className = "char-name-tag";
    nameEl.textContent = data.name;
    this.nameTag = scene.add.dom(wx, wy + tileSize * 0.4, nameEl) as Phaser.GameObjects.DOMElement;
    this.nameTag.setOrigin(0.5, 0).setDepth(30);

    // 血条 / HP
    this.hpBar = scene.add.graphics().setDepth(30);
    if (data.combat) this.drawHpBar(wx, wy, data.combat.hp, data.combat.max_hp, tileSize);

    this.sprite.on("pointerdown", () => scene.events.emit("character-clicked", this.data));
  }

  /** 内层 Phaser 精灵 / Inner Phaser sprite (for camera follow etc.) */
  get rawSprite(): Phaser.GameObjects.Sprite {
    return this.sprite;
  }

  /** 设置深度 / Set depth */
  setDepth(d: number): void {
    this.sprite.setDepth(d);
    if (this.ring) this.ring.setDepth(d + 5);
  }

  /** 获取当前 tile 坐标 / Get current grid position */
  getGridPos(ts: number): { tx: number; ty: number } {
    return {
      tx: Math.floor((this.sprite.x - ts / 2) / ts),
      ty: Math.floor((this.sprite.y - ts / 2) / ts),
    };
  }

  private walkQueue: { wx: number; wy: number }[] = [];
  private walkSpeed = 200;
  private walkOnComplete: (() => void) | null = null; // 全部走完回调 / Path complete callback

  /** 逐格行走 / Step-by-step walk — 追加到队列，支持多段路径连续播放 */
  walkPath(steps: { wx: number; wy: number }[], speed: number, onComplete?: () => void): void {
    if (!steps.length) return;
    this.walkSpeed = speed;
    // 无 pending 队列时设置回调，避免覆盖正在执行的路径的回调 / Only set callback for fresh queue
    const isFresh = this.walkQueue.length === 0 && !this._hasActiveWalkTween();
    if (onComplete && isFresh) this.walkOnComplete = onComplete;
    this.walkQueue.push(...steps);
    if (!this._hasActiveWalkTween()) {
      this.walkNext();
    }
  }

  /** 插队到队列头部 / Prepend steps to the front of the queue */
  prependWalkPath(steps: { wx: number; wy: number }[], speed: number): void {
    this.walkSpeed = speed;
    this.walkQueue.unshift(...steps);
    if (!this._hasActiveWalkTween()) {
      this.walkNext();
    }
  }

  /** 是否有正在播放的行走 tween */
  private _hasActiveWalkTween(): boolean {
    return this.scene.tweens.getTweensOf(this.sprite).length > 0;
  }

  /** 走下一步 / Walk next step */
  private walkNext(): void {
    if (!playState.playing) {
      this._completeWalk();
      return;
    }
    if (this.walkQueue.length === 0) {
      this.walkOnComplete?.();
      this.walkOnComplete = null;
      return;
    }
    const s = this.walkQueue.shift()!;
    const speed = speedMs(this.walkSpeed); // 实时读倍速 / Read speed dynamically
    this.scene.tweens.add({
      targets: this.sprite,
      x: s.wx,
      y: s.wy,
      duration: speed,
      ease: "Linear",
      onUpdate: () => this.updateFollowers(),
      onComplete: () => {
        if (!playState.playing) {
          this._completeWalk();
          return;
        }
        this.walkNext();
      },
    });
  }

  /** 中断当前行走 / Cancel current walk and clear pending queue */
  cancelWalk(): void {
    this.walkQueue = [];
    this.scene.tweens.killTweensOf(this.sprite);
    this._completeWalk();
  }

  /** 清理队列并触发完成回调 / Clear queue and fire completion callback */
  private _completeWalk(): void {
    this.walkQueue = [];
    this.walkOnComplete?.();
    this.walkOnComplete = null;
  }

  /** 是否正在行走 / Whether the sprite has pending steps or an active tween */
  isWalking(): boolean {
    return this.walkQueue.length > 0 || this._hasActiveWalkTween();
  }

  /** 显示对话泡泡 / Show dialogue bubble above character */
  say(text: string, onHide?: () => void): void {
    this.clearBubble();
    const x = this.sprite.x;
    const y = this.sprite.y - this.tileSize * 0.75;
    this.bubble = new DialogueBubble(this.scene, x, y, text, this.data.name, onHide);
  }

  /** 显示探索记录（旁白风格，深色背景浅色字） / Show exploration record bubble (narration style) */
  showExploreRecord(text: string, onHide?: () => void): void {
    this.clearBubble();
    const x = this.sprite.x;
    const y = this.sprite.y - this.tileSize * 0.75;
    this.bubble = new DialogueBubble(this.scene, x, y, text, undefined, onHide, "narration");
  }

  /** 显示思考泡泡（灯泡样式，角色不动） / Show thought bubble (lightbulb style) */
  think(text: string, onHide?: () => void): void {
    this.clearBubble();
    this.thinkCount++;
    const x = this.sprite.x;
    const y = this.sprite.y - this.tileSize * 0.75;
    this.bubble = new DialogueBubble(this.scene, x, y, text, undefined, onHide, "thought");
  }

  /** 获取思考泡泡触发次数 / Get decision bubble trigger count */
  getThinkCount(): number {
    return this.thinkCount;
  }

  /** 当前是否正在显示思考泡泡 / Whether a thought bubble is currently active */
  hasActiveThoughtBubble(): boolean {
    return !!this.bubble && this.bubble.getStyle() === "thought";
  }

  /** 获取当前活跃气泡的样式 / Get active bubble style (null if no bubble) */
  getActiveBubbleStyle(): string | null {
    return this.bubble?.getStyle() ?? null;
  }

  /** 清除当前泡泡 / Clear current bubble */
  clearBubble(): void {
    if (this.bubble) {
      this.bubble.destroy();
      this.bubble = null;
    }
  }

  /** 名字标签、血条、金环跟随精灵 / Followers update with sprite position */
  updateFollowers(): void {
    const x = this.sprite.x,
      y = this.sprite.y,
      ts = this.tileSize;
    this.nameTag.setPosition(x, y + ts * 0.4);
    if (this.ring) {
      this.ring.clear();
      this.ring.lineStyle(2, 0xffd700, 0.8);
      this.ring.strokeCircle(x, y, ts * 0.35);
    }
    if (this.data.combat) {
      this.hpBar.clear();
      this.drawHpBar(x, y, this.data.combat.hp, this.data.combat.max_hp, ts);
    }
    if (this.bubble) {
      this.bubble.setPosition(x, y - ts * 0.75);
    }
  }

  /** 更新血条 / Update HP */
  updateHp(hp: number, maxHp: number): void {
    this.data.combat = { ...this.data.combat!, hp, max_hp: maxHp };
    this.hpBar.clear();
    this.drawHpBar(this.sprite.x, this.sprite.y, hp, maxHp, this.tileSize);
  }

  /** 销毁所有 / Destroy all */
  destroy(): void {
    this.sprite.destroy();
    this.nameTag.destroy();
    this.hpBar.destroy();
    this.ring?.destroy();
    this.bubble?.destroy();
  }

  /** 画血条 / Draw HP bar */
  private drawHpBar(wx: number, wy: number, hp: number, maxHp: number, ts: number): void {
    const bw = 20,
      bh = 3,
      bx = wx - bw / 2,
      by = wy - ts * 0.4 - 6;
    const ratio = Math.max(hp / maxHp, 0);
    this.hpBar.fillStyle(0x333333);
    this.hpBar.fillRect(bx, by, bw, bh); // 背景 / Background
    this.hpBar.fillStyle(ratio > 0.5 ? 0x2ecc71 : ratio > 0.25 ? 0xf39c12 : 0xe74c3c); // 绿/黄/红
    this.hpBar.fillRect(bx, by, bw * ratio, bh); // 血量填充 / HP fill
  }
}
