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
      await this._walkTo(sprite, mm, end.x, end.y);
    }

    // 交互结果不再自动弹出头顶浮字，改为仅记录日志；物体详情由用户点击场景物体后通过 ObjectPanel 查看
    if (narration) {
      log.info(`interact narration: ${pcId} — ${narration}`);
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
