/** Boot 场景单元测试 / Unit tests for Boot scene */
import { describe, expect, it, vi } from "vitest";

// jsdom 没有 canvas，避免 Phaser 全局初始化失败
// jsdom has no canvas; prevent Phaser global initialization failure.
vi.mock("phaser", () => ({
  default: {
    Scene: class {},
  },
}));

const { Boot } = await import("../../../src/scenes/Boot");

vi.mock("../../../src/state/SceneList", () => ({
  sceneList: [
    {
      id: "desert",
      name: "Desert",
      ext_json: JSON.stringify({
        tilemap_url: "/assets/desert.json",
        tileset_url: "/assets/desert.png",
        tileset_image_key: "desert-img",
        tileset_name: "desert-ts",
      }),
    },
    {
      id: "forest",
      name: "Forest",
      ext_json: JSON.stringify({
        tilemap_url: "/assets/forest.json",
        tileset_url: "/assets/desert.png", // 复用 tileset / reuse tileset
        tileset_image_key: "desert-img",
        tileset_name: "desert-ts",
      }),
    },
  ],
}));

describe("Boot", () => {
  function makeBoot() {
    const loaders: { image: any[]; tilemapTiledJSON: any[] } = {
      image: [],
      tilemapTiledJSON: [],
    };
    const scene = {
      load: {
        on: vi.fn(),
        image: vi.fn((key: string, url: string) => loaders.image.push({ key, url })),
        tilemapTiledJSON: vi.fn((key: string, url: string) =>
          loaders.tilemapTiledJSON.push({ key, url })
        ),
      },
      scene: {
        start: vi.fn(),
      },
    };
    const boot = new Boot();
    (boot as any).load = scene.load;
    (boot as any).scene = scene.scene;
    return { boot, scene, loaders };
  }

  it("loads tilemap and tileset for each scene", () => {
    const { boot, loaders } = makeBoot();
    boot.preload();
    expect(loaders.tilemapTiledJSON).toHaveLength(2);
    expect(loaders.tilemapTiledJSON[0]).toEqual({ key: "desert", url: "/assets/desert.json" });
    expect(loaders.tilemapTiledJSON[1]).toEqual({ key: "forest", url: "/assets/forest.json" });
    // tileset 只加载一次 / tileset loaded once
    expect(loaders.image).toHaveLength(1);
    expect(loaders.image[0]).toEqual({ key: "desert-img", url: "/assets/desert.png" });
  });

  it("starts Game scene on create", () => {
    const { boot, scene } = makeBoot();
    boot.create();
    expect(scene.scene.start).toHaveBeenCalledWith("Game");
  });
});
