/** 探索事件处理器 / Explore event handler — 走到终点 + 浮字 + 广播到 NarrativePanel */
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

    // 浮字 + NarrativePanel 广播
    if (exploreRecord) {
      log.info(`explore: ${pcId} — ${exploreRecord}`);
      this._showFloatText(sprite, exploreRecord);
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
    return new Promise((r) => mm.walkTo(sprite, tx, ty, { onComplete: () => r() }));
  }

  /** 轻量浮字，无气泡框 / Lightweight floating text, no bubble */
  private _showFloatText(sprite: CharacterSprite, text: string): Promise<void> {
    return new Promise((resolve) => {
      const scene = this.getScene();
      if (!scene) {
        resolve();
        return;
      }
      const t = scene.add
        .text(sprite.rawSprite.x, sprite.rawSprite.y - 40, text, {
          font: "13px Segoe UI, Microsoft YaHei, sans-serif",
          color: "#a0d8ef",
          stroke: "#000",
          strokeThickness: 2,
        })
        .setOrigin(0.5)
        .setDepth(300)
        .setAlpha(1);
      scene.tweens.add({
        targets: t,
        y: t.y - 30,
        alpha: 0,
        duration: 2500,
        ease: "Power2",
        onComplete: () => {
          t.destroy();
          resolve();
        },
      });
    });
  }
}
