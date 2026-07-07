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
    manager.build("desert", { tilesets: [{ name: "desert", url: "desert.png" }] });
    expect(scene.make.tilemap).toHaveBeenCalledWith({ key: "desert" });
    expect(mockTilemap.addTilesetImage).toHaveBeenCalledWith("desert", "desert");
    expect(manager.tilemap).toBe(mockTilemap);
  });

  it("logs error when tilemap is missing", () => {
    const { scene } = makeScene(false);
    const manager = new MapManager(scene as any);
    manager.build("missing", { tilesets: [{ name: "ts", url: "tk.png" }] });
    expect(manager.tilemap).toBeNull();
  });

  it("logs error when tileset is missing", () => {
    const { scene, mockTilemap } = makeScene(true, false);
    const manager = new MapManager(scene as any);
    manager.build("desert", { tilesets: [{ name: "missing", url: "x.png" }] });
    expect(mockTilemap.addTilesetImage).toHaveBeenCalled();
    expect(manager.tilemap).toBe(mockTilemap);
  });

  it("destroy releases tilemap", () => {
    const { scene, mockTilemap } = makeScene();
    const manager = new MapManager(scene as any);
    manager.build("desert", { tilesets: [{ name: "desert", url: "desert.png" }] });
    manager.destroy();
    expect(mockTilemap.destroy).toHaveBeenCalled();
    expect(manager.tilemap).toBeNull();
  });
});
