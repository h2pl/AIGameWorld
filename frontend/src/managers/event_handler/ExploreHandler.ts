/** 探索事件处理器 / Explore event handler — 按 waypoints 行走并在每点播放旁白 */
import { createLogger } from "../../utils/logger";
const log = createLogger("ExploreHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";

/** 探索路径点 / Explore waypoint */
interface ExploreWaypoint {
  /** 瓦片 X 坐标 / Tile X coordinate */
  x: number;
  /** 瓦片 Y 坐标 / Tile Y coordinate */
  y: number;
  /** 到达该点时播放的旁白 / Narration shown when reaching this point */
  narration?: string;
}

export class ExploreHandler {
  /** 依赖通过 getter 注入，避免强耦合场景实例 / Dependencies injected via getters to avoid tight coupling with the scene */
  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private followSprite: (sprite: any) => void,
    private onNarrative: (text: string) => void
  ) {}

  /** 处理探索事件，逐点行走并播放旁白 / Handle explore event, walk step by step with narrations */
  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as ExploreWaypoint[] | undefined;
    if (!pcId || !waypoints?.length) return;

    const sprite = this.getSprite(pcId);
    if (!sprite) return;
    const mm = this.getMovementManager();
    if (!mm) return;

    /** 镜头跟随探索角色 / Camera follows the exploring character */
    this.followSprite(sprite.rawSprite);

    for (const wp of waypoints) {
      await this._walkTo(sprite, mm, wp.x, wp.y);
      if (wp.narration) {
        log.info(`explore narration: ${pcId} at (${wp.x},${wp.y}) — ${wp.narration}`);
        /** 展示 DM 旁白 / Display DM narration */
        this.onNarrative(wp.narration);
      }
    }
  }

  /** 单点移动，返回 Promise 以支持串行 / Move to a single point, returns a Promise for sequential handling */
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
