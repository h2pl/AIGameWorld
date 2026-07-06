/** 探索事件处理器 / Explore event handler — 从起点走到终点，展示探索记录
 *
 * 数据结构：
 * - waypoints: [{x:start, y:start}, {x:end, y:end}]
 * - explore_record: 第三人称旁白（角色头顶气泡展示）
 */
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
    private followSprite: (sprite: any) => void
  ) {}

  /** 走到终点 → 展示探索记录气泡 / Walk to destination → show explore record bubble */
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

    // 1. 走到终点坐标
    if (waypoints?.length) {
      const mm = this.getMovementManager();
      if (mm) {
        const end = waypoints[waypoints.length - 1];
        await this._walkTo(sprite, mm, end.x, end.y);
      }
    }

    // 2. 角色头顶气泡展示探索记录
    if (exploreRecord) {
      log.info(`explore: ${pcId} — ${exploreRecord}`);
      await this._showBubble(sprite, exploreRecord);
      // 同时广播到 NarrativePanel
      window.dispatchEvent(
        new CustomEvent("tick-event", {
          detail: {
            type: "explore_record",
            payload: { text: `【${pcId}】发现：${exploreRecord}` },
          },
        })
      );
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

  private _showBubble(sprite: CharacterSprite, text: string): Promise<void> {
    return new Promise((resolve) => {
      sprite.showExploreRecord(text, resolve);
    });
  }
}
