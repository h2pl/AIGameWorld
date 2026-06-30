/** 角色精灵 / Character Sprite — 动态纹理 + 血条 + 名字标签 */

import Phaser from "phaser";
import type { CharacterData } from "../types";

export class CharacterSprite {
  readonly id: string;
  readonly data: CharacterData;
  private scene: Phaser.Scene;
  private sprite: Phaser.GameObjects.Sprite;
  private nameTag: Phaser.GameObjects.Text;
  private hpBar: Phaser.GameObjects.Graphics;
  private tileX: number;
  private tileY: number;
  private readonly TS: number;

  constructor(
    scene: Phaser.Scene, data: CharacterData,
    tileX: number, tileY: number, tileSize: number,
  ) {
    this.scene = scene; this.data = data; this.id = data.id;
    this.tileX = tileX; this.tileY = tileY; this.TS = tileSize;

    const cx = tileX * tileSize + tileSize / 2;
    const cy = tileY * tileSize + tileSize / 2;

    // 用角色 id 作为纹理 key（GameScene 已动态生成）/ use character id as texture key
    const textureKey = scene.textures.exists(data.id) ? data.id : (data.is_pc ? "pc_fighter" : "actor_default");
    this.sprite = scene.add.sprite(cx, cy, textureKey).setOrigin(0.5, 0.5).setInteractive({ useHandCursor: true });

    // PC 金边 / Gold ring for PC
    if (data.is_pc) {
      const ring = scene.add.graphics(); ring.lineStyle(2, 0xffd700, 0.8);
      ring.strokeCircle(cx, cy, tileSize * 0.35); ring.setDepth(5);
    }

    // 名字标签 / Name tag
    this.nameTag = scene.add.text(cx, cy + tileSize * 0.45, data.name, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "10px", color: "#fff",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 2, y: 1 },
    }).setOrigin(0.5, 0).setDepth(20);

    // 血条 / HP bar
    this.hpBar = scene.add.graphics().setDepth(20);
    if (data.combat) this.drawHpBar(cx, cy, data.combat.hp, data.combat.max_hp);

    this.sprite.on("pointerdown", () => scene.events.emit("character-clicked", this.data));
  }

  moveTo(tileX: number, tileY: number, duration = 300): Promise<void> {
    return new Promise(resolve => {
      this.tileX = tileX; this.tileY = tileY;
      const cx = tileX * this.TS + this.TS / 2, cy = tileY * this.TS + this.TS / 2;
      this.scene.tweens.add({
        targets: this.sprite, x: cx, y: cy, duration, ease: "Sine.easeInOut",
        onComplete: () => {
          this.nameTag.setPosition(cx, cy + this.TS * 0.45);
          if (this.data.combat) this.drawHpBar(cx, cy, this.data.combat.hp, this.data.combat.max_hp);
          resolve();
        },
      });
    });
  }

  updateHp(hp: number, maxHp: number): void {
    const cx = this.tileX * this.TS + this.TS / 2, cy = this.tileY * this.TS + this.TS / 2;
    this.hpBar.clear(); this.drawHpBar(cx, cy, hp, maxHp);
  }

  destroy(): void {
    this.sprite.destroy(); this.nameTag.destroy(); this.hpBar.destroy();
  }

  private drawHpBar(cx: number, cy: number, hp: number, maxHp: number): void {
    const bw = 20, bh = 3, bx = cx - bw / 2, by = cy - this.TS * 0.4 - 4;
    const ratio = Math.max(hp / maxHp, 0);
    this.hpBar.fillStyle(0x333333); this.hpBar.fillRect(bx, by, bw, bh);
    this.hpBar.fillStyle(ratio > 0.5 ? 0x2ecc71 : ratio > 0.25 ? 0xf39c12 : 0xe74c3c);
    this.hpBar.fillRect(bx, by, bw * ratio, bh);
  }
}
