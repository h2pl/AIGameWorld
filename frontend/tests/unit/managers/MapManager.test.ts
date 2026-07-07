/** MapManager 单元测试 / Unit tests for MapManager */
import { describe, expect, it, vi } from "vitest";
import { MapManager } from "../../../src/managers/MapManager";

describe("MapManager", () => {
  function makeScene(tilemapExists = true, tilesetExists = true) {
    const mockTilemap = {
      widthInPixels: 320,
      heightInPixels: 240,
      addTilesetImage: vi.fn(() => (tilesetExists ? { name: "ts" } : null)),
      createLayer: vi.fn(() => ({
        setCollisionByProperty: vi.fn(),
        setDepth: vi.fn(),
      })),
      destroy: vi.fn(),
    };
    const scene = {
      make: {
        tilemap: vi.fn(() => (tilemapExists ? mockTilemap : null)),
      },
      textures: {
        getTextureKeys: vi.fn(() => []),
      },
      cameras: {
        main: {
          setBounds: vi.fn(),
        },
      },
    };
    return { scene, mockTilemap };
  }

  it("builds tilemap with scene id", () => {
    const { scene, mockTilemap } = makeScene();
    const manager = new MapManager(scene as any);
    manager.build("desert", { tileset_name: "desert", tileset_image_key: "desert-img" });
    expect(scene.make.tilemap).toHaveBeenCalledWith({ key: "desert" });
    expect(mockTilemap.addTilesetImage).toHaveBeenCalledWith("desert", "desert-img");
    expect(manager.tilemap).toBe(mockTilemap);
  });

  it("logs error when tilemap is missing", () => {
    const { scene } = makeScene(false);
    const manager = new MapManager(scene as any);
    manager.build("missing", { tileset_name: "ts", tileset_image_key: "tk" });
    expect(manager.tilemap).toBeNull();
  });

  it("logs error when tileset is missing", () => {
    const { scene, mockTilemap } = makeScene(true, false);
    const manager = new MapManager(scene as any);
    manager.build("desert", { tileset_name: "missing", tileset_image_key: "missing-img" });
    expect(mockTilemap.addTilesetImage).toHaveBeenCalled();
    expect(manager.tilemap).toBe(mockTilemap);
  });

  it("destroy releases tilemap", () => {
    const { scene, mockTilemap } = makeScene();
    const manager = new MapManager(scene as any);
    manager.build("desert", { tileset_name: "desert", tileset_image_key: "desert-img" });
    manager.destroy();
    expect(mockTilemap.destroy).toHaveBeenCalled();
    expect(manager.tilemap).toBeNull();
  });
});
