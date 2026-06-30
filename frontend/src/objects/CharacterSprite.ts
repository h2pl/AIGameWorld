/** 角色精灵 / Character Sprite — 圆形 + 首字母 + 功能色边框 */

import Phaser from "phaser";
import type { CharacterData } from "../types";

export class CharacterSprite {
  readonly id: string;
  readonly data: CharacterData;
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private circle: Phaser.GameObjects.Arc;
  private label: Phaser.GameObjects.Text;
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
    const radius = tileSize * 0.4;
    const borderColor = this.getBorderColor();
    const fillColor = this.getFillColor();

    // 外圈边框 / Border ring
    this.circle = scene.add.arc(0, 0, radius + 2, 0, 360, false, borderColor);
    this.circle.setFillStyle(fillColor);

    // 首字母 / First letter
    const initial = data.name.charAt(0);
    this.label = scene.add.text(0, 0, initial, {
      fontFamily: "Segoe UI, sans-serif",
      fontSize: `${Math.floor(radius)}px`,
      color: "#ffffff",
      fontStyle: "bold",
    }).setOrigin(0.5);

    // 名字标签（下方）/ Name tag (below)
    this.nameTag = scene.add.text(0, radius + 8, data.name, {
      fontFamily: "Segoe UI, sans-serif",
      fontSize: "10px",
      color: "#ffffff",
    }).setOrigin(0.5, 0);

    // 血条 / HP bar
    this.hpBar = scene.add.graphics();
    if (data.combat) {
      this.drawHpBar(cx, cy, data.combat.hp, data.combat.max_hp);
    }

    this.container = scene.add.container(cx, cy, [this.circle, this.label, this.nameTag]);

    // 点击交互 / Click interaction
    this.circle.setInteractive({ useHandCursor: true });
    this.circle.on("pointerdown", () => {
      this.scene.events.emit("character-clicked", this.data);
    });
  }

  /** 移动动画 / Move animation */
  moveTo(tileX: number, tileY: number, duration = 300): Promise<void> {
    return new Promise((resolve) => {
      this.tileX = tileX;
      this.tileY = tileY;
      const cx = tileX * this.TILE_SIZE + this.TILE_SIZE / 2;
      const cy = tileY * this.TILE_SIZE + this.TILE_SIZE / 2;
      this.scene.tweens.add({
        targets: this.container,
        x: cx,
        y: cy,
        duration,
        ease: "Sine.easeInOut",
        onComplete: () => resolve(),
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

  private drawHpBar(cx: number, cy: number, hp: number, maxHp: number): void {
    const bw = 20;
    const bh = 3;
    const bx = cx - bw / 2;
    const by = cy - this.TILE_SIZE * 0.4 - 6;
    const ratio = Math.max(hp / maxHp, 0);
    // 背景 / Background
    this.hpBar.fillStyle(0x333333);
    this.hpBar.fillRect(bx, by, bw, bh);
    // 血量 / HP fill
    const color = ratio > 0.5 ? 0x2ecc71 : ratio > 0.25 ? 0xf39c12 : 0xe74c3c;
    this.hpBar.fillStyle(color);
    this.hpBar.fillRect(bx, by, bw * ratio, bh);
  }

  /** 销毁 / Destroy */
  destroy(): void {
    this.container.destroy();
    this.hpBar.destroy();
  }

  private getBorderColor(): number {
    if (this.data.is_pc) return 0xffd700; // 金边 / Gold
    const map: Record<string, number> = {
      enemy: 0xe74c3c,
      merchant: 0x2ecc71,
      guard: 0xf39c12,
      quest_giver: 0x9b59b6,
    };
    const func = this.data.functions?.[0] || "";
    return map[func] || 0x1abc9c;
  }

  private getFillColor(): number {
    return this.data.is_pc ? 0x3498db : 0x555555;
  }
}
