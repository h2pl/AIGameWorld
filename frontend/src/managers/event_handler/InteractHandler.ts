// -- file start -- / file start
/** 交互事件处理器 / Interact event handler — walk to object + show narration */
import { createLogger } from "../../utils/logger";
const log = createLogger("InteractHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";

interface Waypoint {
  x: number;
  y: number;
}

export class InteractHandler {
  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private followSprite: (sprite: any) => void
  ) {}

  /** 处理交互事件：走到物体旁并播放结果旁白 / Handle interact: walk to object + show narration */
  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as Waypoint[] | undefined;
    const narration = String(payload.narration || "");
    if (!pcId) return;

    const sprite = this.getSprite(pcId);
    if (!sprite) return;
    const mm = this.getMovementManager();
    if (!mm) return;

    this.followSprite(sprite.rawSprite);

    if (waypoints?.length) {
      const end = waypoints[waypoints.length - 1];
      log.info(`walk start: ${pcId} → (${end.x},${end.y}) waypoints=${waypoints.length}`);
      await this._walkTo(sprite, mm, end.x, end.y);
      log.info(`walk done: ${pcId}`);
    }

    // 交互结果用旁白浮字显示，等待消失后才算完成
    if (narration) {
      log.info(`interact narration: ${pcId} — ${narration}`);
      await new Promise<void>((resolve) => sprite.showExploreRecord(narration, resolve));
    }
  }

  private _walkTo(
    sprite: CharacterSprite,
    mm: MovementManager,
    tx: number,
    ty: number
  ): Promise<void> {
    return new Promise((resolve) => {
      mm.walkTo(sprite, tx, ty, { onComplete: () => resolve() });
    });
  }
}
