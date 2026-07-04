/** 角色精灵 / Character Sprite — 世界坐标 + 名字标签 + 血条 + 点击 */

import Phaser from "phaser";
import { DialogueBubble } from "./DialogueBubble";
import type { CharacterData } from "../types";

export class CharacterSprite {
  readonly id: string;
  readonly data: CharacterData;
  private scene: Phaser.Scene;
  private sprite: Phaser.GameObjects.Sprite;           // 主精灵 / Main sprite
  private nameTag: Phaser.GameObjects.Text;             // 名字标签 / Name label
  private hpBar: Phaser.GameObjects.Graphics;           // 血条 / HP bar
  private ring: Phaser.GameObjects.Graphics | null = null; // PC 金环 / Gold ring
  private bubble: DialogueBubble | null = null; // 当前对话泡泡 / Current dialogue bubble
  private tileSize = 32;

  constructor(scene: Phaser.Scene, data: CharacterData, wx: number, wy: number, tileSize: number) {
    this.scene = scene; this.data = data; this.id = data.id; this.tileSize = tileSize;

    // 纹理 / Texture
    const key = scene.textures.exists(data.id) ? data.id : (data.is_pc ? "fighter_fb" : "actor_fb");
    this.sprite = scene.add.sprite(wx, wy, key).setOrigin(0.5, 0.5).setInteractive({ useHandCursor: true });

    // PC 金环 / Gold ring for PC
    if (data.is_pc) {
      this.ring = scene.add.graphics(); this.ring.lineStyle(2, 0xffd700, 0.8);
      this.ring.strokeCircle(wx, wy, tileSize * 0.35);
    }

    // 名字 / Name
    this.nameTag = scene.add.text(wx, wy + tileSize * 0.4, data.name, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "10px", color: "#fff",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 2, y: 1 },
    }).setOrigin(0.5, 0).setDepth(30);

    // 血条 / HP
    this.hpBar = scene.add.graphics().setDepth(30);
    if (data.combat) this.drawHpBar(wx, wy, data.combat.hp, data.combat.max_hp, tileSize);

    this.sprite.on("pointerdown", () => scene.events.emit("character-clicked", this.data));
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

  private walkSteps: { wx: number; wy: number }[] = [];
  private walkSpeed = 200;
  private walkIdx = 0;
  private walkOnComplete: (() => void) | null = null; // 全部走完回调 / Path complete callback

  /** 逐格行走 / Step-by-step walk — 参考 Phaser official complete delay.js 双方法交替模式 */
  walkPath(steps: { wx: number; wy: number }[], speed: number, onComplete?: () => void): void {
    this.walkSteps = steps;
    this.walkSpeed = speed;
    this.walkIdx = 0;
    this.walkOnComplete = onComplete ?? null;
    this.walkNext();
  }

  /** 走下一步 / Walk next step — 与 complete delay.js 相同风格 */
  private walkNext(): void {
    if (this.walkIdx >= this.walkSteps.length) {
      this.walkOnComplete?.();
      this.walkOnComplete = null;
      return;
    }
    const s = this.walkSteps[this.walkIdx++];
    this.scene.tweens.add({
      targets: this.sprite,
      x: s.wx,
      y: s.wy,
      duration: this.walkSpeed,
      ease: "Linear",
      onUpdate: () => this.updateFollowers(),
      onComplete: () => { this.walkNext(); },
    });
  }

  /** 中断当前行走 / Cancel current walk */
  cancelWalk(): void {
    this.walkSteps = [];
    this.walkIdx = 0;
    this.scene.tweens.killTweensOf(this.sprite);
  }

  /** 显示对话泡泡 / Show dialogue bubble above character */
  say(text: string, onHide?: () => void): void {
    this.clearBubble();
    const x = this.sprite.x;
    const y = this.sprite.y - this.tileSize * 0.75;
    this.bubble = new DialogueBubble(this.scene, x, y, text, this.data.name, onHide);
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
    const x = this.sprite.x, y = this.sprite.y, ts = this.tileSize;
    this.nameTag.setPosition(x, y + ts * 0.4);
    if (this.ring) {
      this.ring.clear(); this.ring.lineStyle(2, 0xffd700, 0.8);
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
    this.hpBar.clear(); this.drawHpBar(this.sprite.x, this.sprite.y, hp, maxHp, this.tileSize);
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
    const bw = 20, bh = 3, bx = wx - bw / 2, by = wy - ts * 0.4 - 6;
    const ratio = Math.max(hp / maxHp, 0);
    this.hpBar.fillStyle(0x333333); this.hpBar.fillRect(bx, by, bw, bh);  // 背景 / Background
    this.hpBar.fillStyle(ratio > 0.5 ? 0x2ecc71 : ratio > 0.25 ? 0xf39c12 : 0xe74c3c); // 绿/黄/红
    this.hpBar.fillRect(bx, by, bw * ratio, bh);                           // 血量填充 / HP fill
  }
}
