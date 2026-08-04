/** 地图管理器 / Map Manager — 支持多 tileset、动态图层名、动态 tile_size */
import Phaser from "phaser";
import { DEPTH } from "../constants";
import { createLogger } from "../utils/logger";
const log = createLogger("MapManager");

export class MapManager {
  tilemap: Phaser.Tilemaps.Tilemap | null = null;

  constructor(private scene: Phaser.Scene) {}

  /** 加载并构建 tilemap / Load and build tilemap with layers */
  build(sceneId: string, extJson: Record<string, any>): { mapW: number; mapH: number } {
    const tilesets: Array<{ name: string; url: string }> = extJson.tilesets || [];
    if (tilesets.length === 0 && extJson.tileset_name && extJson.tileset_image_key) {
      tilesets.push({ name: extJson.tileset_name, url: extJson.tileset_image_key });
    }
    const tileSize = extJson.tile_size || 16;

    log.info(`build sceneId=${sceneId} tilesets=%d tile_size=%d`, tilesets.length, tileSize);

    this.tilemap = this.scene.make.tilemap({ key: sceneId });
    if (!this.tilemap) {
      log.error(`tilemap null for key=${sceneId}`);
      return { mapW: 0, mapH: 0 };
    }

    // 添加所有 tileset / Add all tilesets
    const allTilesets: Phaser.Tilemaps.Tileset[] = [];
    for (const ts of tilesets) {
      const t = this.tilemap.addTilesetImage(ts.name, ts.name);
      if (t) {
        allTilesets.push(t);
        log.info(`  tileset OK: %s`, ts.name);
      } else {
        log.error(
          `  tileset FAIL: %s — available: %s`,
          ts.name,
          this.scene.textures.getTextureKeys().join(", ")
        );
      }
    }
    if (allTilesets.length === 0) return { mapW: 0, mapH: 0 };

    // 从 tilemap 官方 API 获取图层名 / Get layer names via official API
    const layerNames: string[] = this.tilemap.getTileLayerNames();
    log.info(`  layers: %s`, layerNames.join(", "));

    // 底层（非 above/overlay 的图层）
    for (const name of layerNames) {
      if (name.toLowerCase().includes("above") || name.toLowerCase() === "overlay") {
        continue;
      }
      const layer = this.tilemap.createLayer(name, allTilesets, 0, 0);
      if (layer) {
        log.info(`  layer OK: %s`, name);
      } else {
        log.error(`  layer FAIL: %s`, name);
      }
    }

    // 顶层（above player）
    const aboveName = layerNames.find(
      (n) => n.toLowerCase().includes("above") || n.toLowerCase() === "overlay"
    );
    if (aboveName) {
      const aboveLayer = this.tilemap.createLayer(aboveName, allTilesets, 0, 0);
      if (aboveLayer) {
        aboveLayer.setDepth(DEPTH.ABOVE_PLAYER);
        log.info(`  above layer OK: %s`, aboveName);
      } else {
        log.error(`  above layer FAIL: %s`, aboveName);
      }
    }

    const mapW = this.tilemap.widthInPixels;
    const mapH = this.tilemap.heightInPixels;
    this.scene.cameras.main.setBounds(0, 0, mapW, mapH);
    log.info(`build OK map=${mapW}x${mapH}px`);
    return { mapW, mapH };
  }

  destroy(): void {
    if (this.tilemap) {
      this.tilemap.destroy();
      this.tilemap = null;
    }
  }
}
