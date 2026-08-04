// -- file start -- / file start
/** 角色移动管理器 / Movement Manager — 统一 A→B 行走逻辑
 *
 * kb/17: Managers — System coordination
 * 所有角色从 A 点走到 B 点（网格坐标）都应经过这里：
 * - 增量同步 tick 更新
 * - explore 路径探索
 * - walk-to-talk 走位对话
 *
 * / Centralizes character movement from tile A to tile B:
 * - incremental sync after tick updates
 * - explore route traversal
 * - walk-to-talk approach
 */
import Phaser from "phaser";
import { CharacterSprite } from "../gameobjects/CharacterSprite";
import { calcSteps } from "../utils/tile";
import { TILEMAP } from "../constants";
import { speedMs } from "../config/playback";

/** 移动完成回调 / Walk completion callback */
type WalkComplete = (finalTx: number, finalTy: number) => void;

export interface MovementOptions {
  /** 每格耗时 ms / Duration per tile in ms */
  speed?: number;
  /** 走完后触发 / Called after reaching destination */
  onComplete?: WalkComplete;
}

export class MovementManager {
  private scene: Phaser.Scene;
  private ts: number;

  constructor(scene: Phaser.Scene, tileSize: number) {
    this.scene = scene;
    this.ts = tileSize;
  }

  /** 从当前位置走到目标 tile（追加到队列）/ Walk from current pos to target tile (append) */
  walkTo(
    sprite: CharacterSprite,
    targetTx: number,
    targetTy: number,
    opts?: MovementOptions
  ): void {
    const from = sprite.getGridPos(this.ts);
    if (from.tx === targetTx && from.ty === targetTy) {
      opts?.onComplete?.(targetTx, targetTy);
      return;
    }
    const steps = calcSteps(from, { tx: targetTx, ty: targetTy }, this.ts);
    const worldSteps = steps.map((s) => ({ wx: s.wx, wy: s.wy }));
    const onComplete = opts?.onComplete ? () => opts.onComplete!(targetTx, targetTy) : undefined;
    sprite.walkPath(worldSteps, speedMs(opts?.speed ?? TILEMAP.WALK_SPEED), onComplete);
  }

  /** 按 waypoint 列表行走（追加到队列）/ Walk through a list of tile waypoints (append) */
  walkRoute(
    sprite: CharacterSprite,
    waypoints: Array<{ x: number; y: number }>,
    opts?: MovementOptions
  ): void {
    if (!waypoints.length) return;
    let current = sprite.getGridPos(this.ts);
    const worldSteps: { wx: number; wy: number }[] = [];
    for (const wp of waypoints) {
      const steps = calcSteps(current, { tx: wp.x, ty: wp.y }, this.ts);
      worldSteps.push(...steps);
      current = { tx: wp.x, ty: wp.y };
    }
    const final = waypoints[waypoints.length - 1];
    const onComplete = opts?.onComplete ? () => opts.onComplete!(final.x, final.y) : undefined;
    sprite.walkPath(worldSteps, speedMs(opts?.speed ?? TILEMAP.WALK_SPEED), onComplete);
  }

  /** 插队走到目标 tile（插到队列前头）/ Walk to target tile, prepended to queue */
  prependWalkTo(
    sprite: CharacterSprite,
    targetTx: number,
    targetTy: number,
    opts?: MovementOptions
  ): void {
    const from = sprite.getGridPos(this.ts);
    if (from.tx === targetTx && from.ty === targetTy) {
      opts?.onComplete?.(targetTx, targetTy);
      return;
    }
    const steps = calcSteps(from, { tx: targetTx, ty: targetTy }, this.ts);
    const worldSteps = steps.map((s) => ({ wx: s.wx, wy: s.wy }));
    // prepend 只支持单段路径；onComplete 由调用方在需要时自行追加
    sprite.prependWalkPath(worldSteps, speedMs(opts?.speed ?? TILEMAP.WALK_SPEED));
  }

  /** 走到目标 tile 的相邻格 / Walk sprite to a tile adjacent to target */
  walkToAdjacent(sprite: CharacterSprite, targetTx: number, targetTy: number): Promise<void> {
    return new Promise((resolve) => {
      const current = sprite.getGridPos(this.ts);
      const adjacent = [
        { tx: targetTx + 1, ty: targetTy },
        { tx: targetTx - 1, ty: targetTy },
        { tx: targetTx, ty: targetTy + 1 },
        { tx: targetTx, ty: targetTy - 1 },
      ].filter((a) => a.tx >= 0 && a.ty >= 0);
      let best = adjacent[0];
      let bestDist = Infinity;
      for (const a of adjacent) {
        const d = Math.abs(a.tx - current.tx) + Math.abs(a.ty - current.ty);
        if (d < bestDist) {
          best = a;
          bestDist = d;
        }
      }
      if (!best) {
        resolve();
        return;
      }
      this.walkTo(sprite, best.tx, best.ty, { onComplete: () => resolve() });
    });
  }
}
