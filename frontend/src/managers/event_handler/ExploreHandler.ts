/** 探索事件处理器 / Explore event handler — 走到终点 + 头顶浮字 */
import { createLogger } from "../../utils/logger";
const log = createLogger("ExploreHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";

interface Waypoint {
  x: number;
  y: number;
}

export class ExploreHandler {
  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private followSprite: (sprite: any) => void,
    private getScene: () => Phaser.Scene
  ) {}

  /** 走到终点 → 浮字 + 广播 / Walk + float text + broadcast */
  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as Waypoint[] | undefined;
    const exploreRecord = String(payload.explore_record || "");
    if (!pcId) return;

    const sprite = this.getSprite(pcId); // 探索者精灵
    if (!sprite) return;

    this.followSprite(sprite.rawSprite); // 镜头跟随

    // 走到终点
    if (waypoints?.length) {
      const mm = this.getMovementManager();
      if (mm) {
        const end = waypoints[waypoints.length - 1];
        await this._walkTo(sprite, mm, end.x, end.y);
      }
    }
    // 浮字
    if (exploreRecord) {
      log.info(`explore: ${pcId} — ${exploreRecord}`);
      await new Promise<void>((resolve) => sprite.showExploreRecord(exploreRecord, resolve));
    }
  }

  private _walkTo(
    sprite: CharacterSprite,
    mm: MovementManager,
    tx: number,
    ty: number
  ): Promise<void> {
    return new Promise((r) => mm.walkTo(sprite, tx, ty, { onComplete: () => r() }));
  }
}
