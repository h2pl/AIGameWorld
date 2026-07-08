// -- file start -- / file start
/** 战斗事件处理器 / Combat event handler — walk to target + show combat narration */
import { createLogger } from "../../utils/logger";
const log = createLogger("CombatHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { ActorManager } from "../ActorManager";
import type { EventData } from "../../types";

interface Waypoint {
  x: number;
  y: number;
}

export class CombatHandler {
  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private getActorManager: () => ActorManager | undefined,
    private followSprite: (sprite: any) => void
  ) {}

  /** 处理战斗事件：走到目标旁、播放战斗旁白、击败则移除目标 / Handle combat: walk, narrate, remove defeated target */
  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as Waypoint[] | undefined;
    const narration = String(payload.narration || "");
    const targetId = String(payload.target_id || "");
    const targetType = String(payload.target_type || "");
    const targetDefeated = Boolean(payload.target_defeated);
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

    if (narration) {
      log.info(`combat narration: ${pcId} → ${targetId || "?"} — ${narration}`);
      // 战斗旁白加 ⚔️ 图标 / Combat narration with ⚔️ icon
      await new Promise<void>((resolve) => sprite.showExploreRecord(`⚔️ ${narration}`, resolve));
    }

    // 如果目标被击败且是 actor，从场景中移除 / Remove defeated actor from scene
    if (targetDefeated && targetType === "actor" && targetId) {
      this.getActorManager()?.remove(targetId);
      log.info(`actor defeated and removed: ${targetId}`);
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
