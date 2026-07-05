/** 探索事件处理器 / Explore event handler — 播放 waypoints 路径行走动画 */
import { createLogger } from "../../utils/logger";
const log = createLogger("ExploreHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";

export class ExploreHandler {
  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private followSprite: (sprite: any) => void
  ) {}

  /** 处理探索事件，按 waypoints 走路径 / Handle explore event, walk along waypoints */
  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as Array<{ x: number; y: number }> | undefined;
    if (!pcId || !waypoints?.length) return;

    const sprite = this.getSprite(pcId);
    if (!sprite) return;
    const mm = this.getMovementManager();
    if (!mm) return;

    const last = waypoints[waypoints.length - 1];
    this.followSprite(sprite.rawSprite);
    return new Promise((resolve) => {
      mm.walkRoute(sprite, waypoints, {
        onComplete: () => {
          log.info(`explore done: ${pcId} → (${last.x},${last.y})`);
          resolve();
        },
      });
    });
  }
}
