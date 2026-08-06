/** PC 精灵管理器 / PC sprite manager */
import Phaser from "phaser";
import { CharacterSprite } from "../gameobjects/CharacterSprite";
import { gridToWorld } from "../utils/tile";
import { DEPTH } from "../constants";

export class PcManager {
  sprites: Map<string, CharacterSprite> = new Map();
  private scene: Phaser.Scene;
  private ts: number;

  constructor(scene: Phaser.Scene, tileSize: number) {
    this.scene = scene;
    this.ts = tileSize;
  }

  /** 批量创建 PC 精灵 / Create all PC sprites from data */
  createAll(chars: any[]): void {
    for (const ch of chars) {
      const p = { x: ch.position_x, y: ch.position_y };
      const { wx, wy } = gridToWorld(p.x, p.y, this.ts);
      const sp = new CharacterSprite(this.scene, ch, wx, wy, this.ts);
      sp.setDepth(DEPTH.CHARACTER);
      this.sprites.set(ch.id, sp);
    }
  }

  /** 按 id 获取精灵 / Get sprite by id */
  getSprite(id: string): CharacterSprite | undefined {
    return this.sprites.get(id);
  }

  /** 计算 PC 群中心点（世界坐标）/ Calculate PC group center in world coords */
  calcCameraCenter(_zoom: number): { cx: number; cy: number } {
    let minX = 99,
      minY = 99,
      maxX = -99,
      maxY = -99;
    this.sprites.forEach((sp) => {
      const { tx, ty } = sp.getGridPos(this.ts);
      minX = Math.min(minX, tx);
      maxX = Math.max(maxX, tx);
      minY = Math.min(minY, ty);
      maxY = Math.max(maxY, ty);
    });
    if (minX > maxX) return { cx: 0, cy: 0 };
    return {
      cx: ((minX + maxX) / 2 + 0.5) * this.ts,
      cy: ((minY + maxY) / 2 + 0.5) * this.ts,
    };
  }

  /** 销毁所有精灵 / Destroy all sprites */
  destroy(): void {
    this.sprites.forEach((sp) => sp.destroy());
    this.sprites.clear();
  }
}
