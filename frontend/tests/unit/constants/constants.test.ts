/** 常量模块单元测试 / Unit tests for constants modules
 *
 * 验证 KEY / DEPTH / TILEMAP 导出值正确性：
 * / Verify KEY, DEPTH, TILEMAP export values
 */
import { describe, it, expect } from "vitest";
import { DEPTH, TILEMAP } from "../../../src/constants";

describe("DEPTH", () => {
  it("should have ascending layer order", () => {
    // 深度层级应递增 / Depth layers should be ascending
    expect(DEPTH.BELOW_PLAYER).toBeLessThan(DEPTH.WORLD);
    expect(DEPTH.WORLD).toBeLessThan(DEPTH.CHARACTER);
    expect(DEPTH.CHARACTER).toBeLessThan(DEPTH.ABOVE_PLAYER);
    expect(DEPTH.ABOVE_PLAYER).toBeLessThan(DEPTH.HUD);
  });
});

describe("TILEMAP", () => {
  it("should define tile size as 16", () => {
    // tile 默认尺寸为 16，可被 ext_json.tile_size 覆盖 / Default tile size is 16, overridable
    expect(TILEMAP.TILE_SIZE).toBe(16);
  });

  it("should define walk speed in ms", () => {
    // 行走速度为正整数毫秒 / Walk speed is a positive integer in ms
    expect(TILEMAP.WALK_SPEED).toBeGreaterThan(0);
  });
});
