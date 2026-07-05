/** 探索事件处理器 / Explore event handler */
import type { CharacterManager } from "../CharacterManager";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";

export class ExploreHandler {
  constructor(
    private getCharManager: () => CharacterManager | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private followSprite: (sprite: any) => void
  ) {}

  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;

    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as Array<{ x: number; y: number }> | undefined;
    const finalX = Number(payload.final_x ?? 0);
    const finalY = Number(payload.final_y ?? 0);
    if (!pcId || !waypoints?.length) return;

    const sprite = this.getCharManager()?.getSprite(pcId);
    if (!sprite) return;
    const movementManager = this.getMovementManager();
    if (!movementManager) return;

    // 镜头跟随当前探索角色 / Camera follows exploring PC
    this.followSprite(sprite.rawSprite);

    const allWaypoints = [...waypoints, { x: finalX, y: finalY }];
    return new Promise((resolve) => {
      movementManager.walkRoute(sprite, allWaypoints, {
        onComplete: () => {
          console.log("[ExploreHandler] explore done: %s → (%d,%d)", pcId, finalX, finalY);
          resolve();
        },
      });
    });
  }
}
