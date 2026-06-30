/** 角色精灵 / Character Sprite — 世界坐标 + 名字标签 + 血条 + 点击 */

import Phaser from "phaser";
import type { CharacterData } from "../types";

export class CharacterSprite {
  readonly id: string;
  readonly data: CharacterData;
  private scene: Phaser.Scene;
  private sprite: Phaser.GameObjects.Sprite;           // 主精灵 / Main sprite
  private nameTag: Phaser.GameObjects.Text;             // 名字标签 / Name label
  private hpBar: Phaser.GameObjects.Graphics;           // 血条 / HP bar
  private worldX = 0;                                   // 世界坐标 / World X
  private worldY = 0;                                   // 世界坐标 / World Y

  constructor(scene: Phaser.Scene, data: CharacterData, wx: number, wy: number, tileSize: number) {
    this.scene = scene; this.data = data; this.id = data.id; // 初始化 / Init
    this.worldX = wx; this.worldY = wy;

    // 纹理 / Texture
    const key = scene.textures.exists(data.id) ? data.id : (data.is_pc ? "pc_fighter" : "actor_default");
    this.sprite = scene.add.sprite(wx, wy, key).setOrigin(0.5, 0.5).setInteractive({ useHandCursor: true });

    // PC 金环 / Gold ring for PC
    if (data.is_pc) {
      const ring = scene.add.graphics(); ring.lineStyle(2, 0xffd700, 0.8);
      ring.strokeCircle(wx, wy, tileSize * 0.35);
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
  setDepth(d: number): void { this.sprite.setDepth(d); }

  /** 世界坐标移动 / Move in world coords */
  moveToWorld(wx: number, wy: number, duration = 300): Promise<void> {
    return new Promise(resolve => {
      this.worldX = wx; this.worldY = wy;
      this.scene.tweens.add({
        targets: this.sprite, x: wx, y: wy, duration, ease: "Sine.easeInOut",
        onComplete: () => { this.nameTag.setPosition(wx, wy + 14); resolve(); }, // 更新名字位置
      });
    });
  }

  /** 更新血条 / Update HP */
  updateHp(hp: number, maxHp: number): void {
    this.hpBar.clear(); this.drawHpBar(this.worldX, this.worldY, hp, maxHp, 32);
  }

  /** 销毁 / Destroy */
  destroy(): void { this.sprite.destroy(); this.nameTag.destroy(); this.hpBar.destroy(); }

  /** 画血条 / Draw HP bar */
  private drawHpBar(wx: number, wy: number, hp: number, maxHp: number, ts: number): void {
    const bw = 20, bh = 3, bx = wx - bw / 2, by = wy - ts * 0.4 - 6; // 位置计算 / Position calc
    const ratio = Math.max(hp / maxHp, 0);                              // 血量比例 / HP ratio
    this.hpBar.fillStyle(0x333333); this.hpBar.fillRect(bx, by, bw, bh); // 背景 / Background
    this.hpBar.fillStyle(ratio > 0.5 ? 0x2ecc71 : ratio > 0.25 ? 0xf39c12 : 0xe74c3c); // 绿/黄/红
    this.hpBar.fillRect(bx, by, bw * ratio, bh);                        // 血量填充 / HP fill
  }
}
