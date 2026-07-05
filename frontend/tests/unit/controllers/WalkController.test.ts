/** WalkController 单元测试 / Unit tests for WalkController */

import { describe, it, expect, vi } from "vitest";
import { WalkController } from "../../../src/controllers/WalkController";
import { TILEMAP } from "../../../src/constants";

const TILE_SIZE = 32;

/** 轻量 mock CharacterSprite / Lightweight mock CharacterSprite
 *  只暴露 walkPath/prependWalkPath/getGridPos，用于不依赖 Phaser 的单元测试
 *  Only exposes minimal methods needed for Phaser-free unit tests
 */
function makeMockSprite(startTx: number, startTy: number) {
  return {
    x: startTx * TILE_SIZE + TILE_SIZE / 2,
    y: startTy * TILE_SIZE + TILE_SIZE / 2,
    walkQueue: [] as Array<{ wx: number; wy: number }>,
    walkSpeed: 0,
    walkOnComplete: null as ((finalTx: number, finalTy: number) => void) | null,
    getGridPos() {
      return {
        tx: Math.floor((this.x - TILE_SIZE / 2) / TILE_SIZE),
        ty: Math.floor((this.y - TILE_SIZE / 2) / TILE_SIZE),
      };
    },
    walkPath(steps: Array<{ wx: number; wy: number }>, speed: number, onComplete?: () => void) {
      this.walkQueue.push(...steps);
      this.walkSpeed = speed;
      if (onComplete) {
        const last = steps[steps.length - 1];
        this.walkOnComplete = () => {
          onComplete();
          if (last) {
            this.x = last.wx;
            this.y = last.wy;
          }
        };
      }
    },
    prependWalkPath(steps: Array<{ wx: number; wy: number }>, speed: number) {
      this.walkQueue.unshift(...steps);
      this.walkSpeed = speed;
    },
  };
}

describe("WalkController", () => {
  /** 每个用例构造独立 controller / Each test gets a fresh controller */
  function makeCtrl() {
    const scene = { tweens: { getTweensOf: vi.fn(() => []) } } as any;
    return new WalkController(scene, TILE_SIZE);
  }

  it("walkTo appends steps to target tile", () => {
    const sprite = makeMockSprite(0, 0);
    const ctrl = makeCtrl();

    ctrl.walkTo(sprite as any, 2, 0);
    expect(sprite.walkQueue.length).toBeGreaterThan(0);
    const last = sprite.walkQueue[sprite.walkQueue.length - 1];
    expect(last.wx).toBe(2 * TILE_SIZE + TILE_SIZE / 2);
    expect(last.wy).toBe(0 * TILE_SIZE + TILE_SIZE / 2);
    expect(sprite.walkSpeed).toBe(TILEMAP.WALK_SPEED);
  });

  it("walkTo immediately completes if already at target", () => {
    const sprite = makeMockSprite(5, 5);
    const ctrl = makeCtrl();
    const cb = vi.fn();

    ctrl.walkTo(sprite as any, 5, 5, { onComplete: cb });
    expect(sprite.walkQueue.length).toBe(0);
    expect(cb).toHaveBeenCalledWith(5, 5);
  });

  it("walkRoute converts tile waypoints to world steps", () => {
    const sprite = makeMockSprite(0, 0);
    const ctrl = makeCtrl();

    ctrl.walkRoute(sprite as any, [
      { x: 1, y: 0 },
      { x: 1, y: 2 },
    ]);
    expect(sprite.walkQueue.length).toBeGreaterThan(0);
    const last = sprite.walkQueue[sprite.walkQueue.length - 1];
    expect(last.wx).toBe(1 * TILE_SIZE + TILE_SIZE / 2);
    expect(last.wy).toBe(2 * TILE_SIZE + TILE_SIZE / 2);
  });

  it("prependWalkTo prepends steps to queue", () => {
    const sprite = makeMockSprite(0, 0);
    const ctrl = makeCtrl();

    ctrl.prependWalkTo(sprite as any, 2, 0);
    expect(sprite.walkQueue.length).toBeGreaterThan(0);
    const first = sprite.walkQueue[0];
    expect(first.wx).toBe(1 * TILE_SIZE + TILE_SIZE / 2);
  });

  it("walkRoute calls onComplete with final tile", () => {
    const sprite = makeMockSprite(0, 0);
    const ctrl = makeCtrl();
    const cb = vi.fn();

    ctrl.walkRoute(sprite as any, [{ x: 3, y: 3 }], { onComplete: cb });
    expect(sprite.walkOnComplete).toBeTypeOf("function");
    sprite.walkOnComplete?.(3, 3);
    expect(cb).toHaveBeenCalledWith(3, 3);
  });
});
