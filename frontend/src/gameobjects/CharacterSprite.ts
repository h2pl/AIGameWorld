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
  private ring: Phaser.GameObjects.Graphics | null = null; // PC 金环 / Gold ring
  private tileSize = 32;

  constructor(scene: Phaser.Scene, data: CharacterData, wx: number, wy: number, tileSize: number) {
    this.scene = scene; this.data = data; this.id = data.id; this.tileSize = tileSize;

    // 纹理 / Texture
    const key = scene.textures.exists(data.id) ? data.id : (data.is_pc ? "pc_fighter" : "actor_default");
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

  /** 世界坐标移动 + 关联对象跟随 / Move in world coords, followers follow */
  moveToWorld(wx: number, wy: number, duration = 300): Promise<void> {
    return new Promise(resolve => {
      this.scene.tweens.add({
        targets: this.sprite, x: wx, y: wy, duration, ease: "Sine.easeInOut",
        onUpdate: () => {
          // 让名字标签跟随精灵当前位置 / Let name tag follow sprite's current position
          this.nameTag.setPosition(this.sprite.x, this.sprite.y + this.tileSize * 0.4);
          // 金环跟随 / Ring follows
          if (this.ring) {
            this.ring.clear(); this.ring.lineStyle(2, 0xffd700, 0.8);
            this.ring.strokeCircle(this.sprite.x, this.sprite.y, this.tileSize * 0.35);
          }
          // 血条跟随 / HP bar follows
          if (this.data.combat) {
            this.hpBar.clear();
            this.drawHpBar(this.sprite.x, this.sprite.y, this.data.combat.hp, this.data.combat.max_hp, this.tileSize);
          }
        },
        onComplete: () => resolve(),
      });
    });
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
