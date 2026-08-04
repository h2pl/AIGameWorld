/** 坐标工具单元测试 / Unit tests for tile coordinate utilities
 *
 * 覆盖 gridToWorld / worldToGrid / calcSteps 三种场景：
 * / Covers gridToWorld, worldToGrid, and calcSteps scenarios:
 * - 原点与远点转换 / Origin and distant tile conversion
 * - 相邻格与对角线路径 / Adjacent and diagonal path generation
 */
import { describe, it, expect } from "vitest";
import { gridToWorld, worldToGrid, calcSteps } from "../../../src/utils/tile";

// 测试用 tile 尺寸 / Tile size used in tests
const TILE_SIZE = 32;

describe("gridToWorld", () => {
  it("should return pixel center for tile (0, 0)", () => {
    // 左上角 tile 中心像素 / Top-left tile center pixel
    expect(gridToWorld(0, 0, TILE_SIZE)).toEqual({ wx: 16, wy: 16 });
  });

  it("should return pixel center for tile (1, 2)", () => {
    // 普通 tile 中心像素 / Common tile center pixel
    expect(gridToWorld(1, 2, TILE_SIZE)).toEqual({ wx: 48, wy: 80 });
  });
});

describe("worldToGrid", () => {
  it("should convert pixel center back to tile coordinate", () => {
    // 像素中心应落在对应 tile / Pixel center maps to its tile
    expect(worldToGrid(16, 16, TILE_SIZE)).toEqual({ tx: 0, ty: 0 });
  });

  it("should convert bottom-right pixel to tile (1, 1)", () => {
    // tile 右下角像素应归属下一 tile / Bottom-right pixel belongs to next tile
    expect(worldToGrid(63, 63, TILE_SIZE)).toEqual({ tx: 1, ty: 1 });
  });
});

describe("calcSteps", () => {
  it("should return a single target step for adjacent tiles", () => {
    // 相邻格直接走到目标 / Adjacent tile goes directly to target
    const steps = calcSteps({ tx: 0, ty: 0 }, { tx: 1, ty: 0 }, TILE_SIZE);
    expect(steps).toHaveLength(1);
    expect(steps[0]).toEqual({ wx: 48, wy: 16 });
  });

  it("should return intermediate steps for diagonal movement", () => {
    // 对角线移动生成中间 step / Diagonal movement generates intermediate steps
    const steps = calcSteps({ tx: 0, ty: 0 }, { tx: 2, ty: 2 }, TILE_SIZE);
    expect(steps).toHaveLength(2);
    expect(steps[0]).toEqual({ wx: 48, wy: 48 });
    expect(steps[1]).toEqual({ wx: 80, wy: 80 });
  });
});
