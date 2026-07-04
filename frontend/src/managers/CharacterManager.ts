/** 角色生命周期管理 / Character lifecycle manager */
/** kb/17: Managers — System coordination */

import Phaser from "phaser";
import { CharacterSprite } from "../gameobjects/CharacterSprite";
import { gridToWorld, calcSteps } from "../utils/tile";
import { TILEMAP, DEPTH } from "../constants";
import type { CharacterData } from "../types";

type Pos = { x: number; y: number };

export class CharacterManager {
  private sprites: Map<string, CharacterSprite> = new Map();
  private scene: Phaser.Scene;
  private ts: number;

  constructor(scene: Phaser.Scene, tileSize: number) {
    this.scene = scene;
    this.ts = tileSize;
  }

  /** 首次批量创建所有角色 / Create all characters initially */
  createAll(chars: CharacterData[], posMap: Record<string, Pos>): void {
    for (const ch of chars) {
      const p = posMap[ch.id] || { x: ch.position_x, y: ch.position_y };
      const { wx, wy } = gridToWorld(p.x, p.y, this.ts);
      const sp = new CharacterSprite(this.scene, ch, wx, wy, this.ts);
      sp.setDepth(DEPTH.CHARACTER);
      this.sprites.set(ch.id, sp);
    }
  }

  /** WS tick 后增量同步：移动现有 / 创建新增 / 删除离场 / Incremental sync */
  sync(chars: CharacterData[], posMap: Record<string, Pos>): void {
    const currentIds = new Set(chars.map(c => c.id));

    // 删除 / Remove
    for (const [id, sp] of this.sprites) {
      if (!currentIds.has(id)) { sp.destroy(); this.sprites.delete(id); }
    }

    // 创建或移动 / Create or move
    for (const ch of chars) {
      const p = posMap[ch.id] || { x: ch.position_x, y: ch.position_y };
      const { wx, wy } = gridToWorld(p.x, p.y, this.ts);
      const existing = this.sprites.get(ch.id);
      if (existing) {
        const old = existing.getGridPos(this.ts);
        if (old.tx !== p.x || old.ty !== p.y) {
          existing.cancelWalk();
          const steps = calcSteps(old, { tx: p.x, ty: p.y }, this.ts);
          existing.walkPath(steps, TILEMAP.WALK_SPEED);
        }
        if (ch.combat) existing.updateHp(ch.combat.hp, ch.combat.max_hp);
      } else {
        const sp = new CharacterSprite(this.scene, ch, wx, wy, this.ts);
        sp.setDepth(DEPTH.CHARACTER);
        this.sprites.set(ch.id, sp);
      }
    }
  }

  /** 计算摄像机包围盒 / Calc camera bounding box for scroll */
  calcCameraScroll(canvasW: number, canvasH: number): { sx: number; sy: number } {
    let minX = 99, minY = 99, maxX = -99, maxY = -99;
    this.sprites.forEach(sp => {
      const { tx, ty } = sp.getGridPos(this.ts);
      minX = Math.min(minX, tx); maxX = Math.max(maxX, tx);
      minY = Math.min(minY, ty); maxY = Math.max(maxY, ty);
    });
    if (minX > maxX) return { sx: 0, sy: 0 };
    const mx = ((minX + maxX) / 2 + 0.5) * this.ts;
    const my = ((minY + maxY) / 2 + 0.5) * this.ts;
    return { sx: mx - canvasW / 2, sy: my - canvasH / 2 };
  }

  /** 按 id 获取角色精灵 / Get character sprite by id */
  getSprite(id: string): CharacterSprite | undefined {
    return this.sprites.get(id);
  }

  /** 清除所有角色头顶泡泡 / Clear all dialogue bubbles */
  clearBubbles(): void {
    this.sprites.forEach(sp => sp.clearBubble());
  }

  /** 销毁所有 / Destroy all */
  destroy(): void {
    this.sprites.forEach(sp => sp.destroy());
    this.sprites.clear();
  }
}
