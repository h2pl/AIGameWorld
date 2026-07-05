/** Actor 精灵管理器 / Actor sprite manager */
import Phaser from "phaser";
import { CharacterSprite } from "../gameobjects/CharacterSprite";
import { gridToWorld } from "../utils/tile";
import { DEPTH } from "../constants";

export class ActorManager {
  sprites: Map<string, CharacterSprite> = new Map();
  private scene: Phaser.Scene;
  private ts: number;

  constructor(scene: Phaser.Scene, tileSize: number) { this.scene = scene; this.ts = tileSize; }

  /** 批量创建 Actor 精灵 / Create all actor sprites from data */
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
  getSprite(id: string): CharacterSprite | undefined { return this.sprites.get(id); }

  /** 销毁所有精灵 / Destroy all sprites */
  destroy(): void { this.sprites.forEach((sp) => sp.destroy()); this.sprites.clear(); }
}
