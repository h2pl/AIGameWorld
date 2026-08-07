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
      getTileLayerNames: vi.fn(() => ["Below Player", "World", "Above Player"]),
      destroy: vi.fn(),
    };
    const scene = {
      make: {
        tilemap: vi.fn(() => (tilemapExists ? mockTilemap : null)),
      },
      textures: {
        getTextureKeys: vi.fn(() => []),
        get: vi.fn(() => ({ setFilter: vi.fn() })),
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

  it("falls back when tilemap missing", () => {
    const { scene } = makeScene(false);
    const manager = new MapManager(scene as any);
    manager.build("desert", { tilesets: [{ name: "desert", url: "desert.png" }] });
    expect(manager.tilemap).toBeNull();
  });

  it("applies NEAREST filter to each tileset", () => {
    const { scene, mockTilemap } = makeScene();
    const manager = new MapManager(scene as any);
    manager.build("desert", {
      tilesets: [
        { name: "desert", url: "desert.png" },
        { name: "props", url: "props.png" },
      ],
    });
    expect(scene.textures.get).toHaveBeenCalledWith("desert");
    expect(scene.textures.get).toHaveBeenCalledWith("props");
    expect(mockTilemap.addTilesetImage).toHaveBeenCalledTimes(2);
  });
});
