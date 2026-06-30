/** 角色精灵 / Character Sprite — tileset 风格 + 血条 + 名字标签 */

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
  private readonly TILE_SIZE: number;

  constructor(
    scene: Phaser.Scene,
    data: CharacterData,
    tileX: number,
    tileY: number,
    tileSize: number,
  ) {
    this.scene = scene;
    this.data = data;
    this.id = data.id;
    this.tileX = tileX;
    this.tileY = tileY;
    this.TILE_SIZE = tileSize;

    const cx = tileX * tileSize + tileSize / 2;
    const cy = tileY * tileSize + tileSize / 2;

    // Sprite 纹理 / Sprite texture key
    const textureKey = data.is_pc ? this.getPcTextureKey() : "actor_default";
    this.sprite = scene.add.sprite(cx, cy, textureKey);
    this.sprite.setOrigin(0.5, 0.5);
    this.sprite.setInteractive({ useHandCursor: true });

    // PC 金边 / Gold border for PC
    if (data.is_pc) {
      this.sprite.setTint(0xffffff); // 正常颜色
      // Draw gold selection ring
      const ring = scene.add.graphics();
      ring.lineStyle(2, 0xffd700, 0.8);
      ring.strokeCircle(cx, cy, tileSize * 0.35);
      ring.setDepth(5);
    }

    // Name tag / 名字标签
    this.nameTag = scene.add.text(cx, cy + tileSize * 0.45, data.name, {
      fontFamily: "Segoe UI, sans-serif",
      fontSize: "10px",
      color: "#ffffff",
      backgroundColor: "rgba(0,0,0,0.6)",
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5, 0).setDepth(20);

    // HP bar / 血条
    this.hpBar = scene.add.graphics().setDepth(20);
    if (data.combat) {
      this.drawHpBar(cx, cy, data.combat.hp, data.combat.max_hp);
    }

    // Click / 点击
    this.sprite.on("pointerdown", () => {
      scene.events.emit("character-clicked", this.data);
    });
  }

  /** 移动动画 / Move to position */
  moveTo(tileX: number, tileY: number, duration = 300): Promise<void> {
    return new Promise((resolve) => {
      this.tileX = tileX;
      this.tileY = tileY;
      const cx = tileX * this.TILE_SIZE + this.TILE_SIZE / 2;
      const cy = tileY * this.TILE_SIZE + this.TILE_SIZE / 2;
      this.scene.tweens.add({
        targets: this.sprite,
        x: cx,
        y: cy,
        duration,
        ease: "Sine.easeInOut",
        onComplete: () => {
          this.nameTag.setPosition(cx, cy + this.TILE_SIZE * 0.45);
          if (this.data.combat) {
            this.drawHpBar(cx, cy, this.data.combat.hp, this.data.combat.max_hp);
          }
          resolve();
        },
      });
    });
  }

  /** 更新血条 / Update HP bar */
  updateHp(hp: number, maxHp: number): void {
    const cx = this.tileX * this.TILE_SIZE + this.TILE_SIZE / 2;
    const cy = this.tileY * this.TILE_SIZE + this.TILE_SIZE / 2;
    this.hpBar.clear();
    this.drawHpBar(cx, cy, hp, maxHp);
  }

  /** 销毁 / Destroy */
  destroy(): void {
    this.sprite.destroy();
    this.nameTag.destroy();
    this.hpBar.destroy();
  }

  private drawHpBar(cx: number, cy: number, hp: number, maxHp: number): void {
    const bw = 20;
    const bh = 3;
    const bx = cx - bw / 2;
    const by = cy - this.TILE_SIZE * 0.4 - 4;
    const ratio = Math.max(hp / maxHp, 0);
    this.hpBar.fillStyle(0x333333);
    this.hpBar.fillRect(bx, by, bw, bh);
    const color = ratio > 0.5 ? 0x2ecc71 : ratio > 0.25 ? 0xf39c12 : 0xe74c3c;
    this.hpBar.fillStyle(color);
    this.hpBar.fillRect(bx, by, bw * ratio, bh);
  }

  private getPcTextureKey(): string {
    const roleMap: Record<string, string> = {
      fighter: "pc_fighter",
      rogue: "pc_rogue",
      cleric: "pc_cleric",
      wizard: "pc_wizard",
    };
    return roleMap[this.data.role] || "pc_fighter";
  }
}
