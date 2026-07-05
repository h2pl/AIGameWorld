/** 常量模块单元测试 / Unit tests for constants modules
 *
 * 验证 KEY / SCENE_MAP / DEPTH / TILEMAP 导出值正确性：
 * / Verify KEY, SCENE_MAP, DEPTH, TILEMAP export values
 */
import { describe, it, expect } from "vitest";
import { KEY, SCENE_MAP, DEPTH, TILEMAP } from "../../../src/constants";

describe("KEY", () => {
  it("should define image and tilemap cache keys", () => {
    // 图片和地图缓存键应存在 / Image and tilemap cache keys should exist
    expect(KEY.IMAGE.TUXEMON).toBe("tuxemon");
    expect(KEY.TILEMAP.TUXEMON).toBe("tuxemon-map");
  });
});

describe("SCENE_MAP", () => {
  it("should map village_elderwood to tuxemon-map", () => {
    // village 场景映射到 tuxemon 地图 / Village scene maps to tuxemon map
    expect(SCENE_MAP.village_elderwood.map).toBe("tuxemon-map");
    expect(SCENE_MAP.village_elderwood.spawn).toEqual({ x: 20, y: 20 });
  });

  it("should map desert to desert-map", () => {
    // desert 场景映射到 desert 地图 / Desert scene maps to desert map
    expect(SCENE_MAP.desert.map).toBe("desert-map");
  });
});

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
  it("should define tile size as 32", () => {
    // tile 尺寸固定为 32 / Tile size is fixed at 32
    expect(TILEMAP.TILE_SIZE).toBe(32);
  });

  it("should define walk speed in ms", () => {
    // 行走速度为正整数毫秒 / Walk speed is a positive integer in ms
    expect(TILEMAP.WALK_SPEED).toBeGreaterThan(0);
  });
});
