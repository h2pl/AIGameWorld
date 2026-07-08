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

    const sprite = this.getSprite(pcId);
    if (!sprite) return;

    this.followSprite(sprite.rawSprite);

    // waypoints = [start, end]，从 sprite 当前位置走到终点
    if (waypoints?.length) {
      const mm = this.getMovementManager();
      if (mm) {
        const dest = waypoints[waypoints.length - 1];
        await new Promise<void>((r) =>
          mm.walkTo(sprite, dest.x, dest.y, { onComplete: () => r() })
        );
      }
    }

    // 浮字
    if (exploreRecord) {
      log.info(`explore: ${pcId} — ${exploreRecord}`);
      await new Promise<void>((resolve) =>
        sprite.showExploreRecord(`🔍 ${exploreRecord}`, resolve)
      );
    }
  }
}
