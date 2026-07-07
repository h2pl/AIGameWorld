/** 地图管理器 / Map Manager — 支持多 tileset、动态图层名、动态 tile_size */
import Phaser from "phaser";
import { DEPTH } from "../constants";
import { createLogger } from "../utils/logger";
const log = createLogger("MapManager");

export class MapManager {
  tilemap: Phaser.Tilemaps.Tilemap | null = null;

  constructor(private scene: Phaser.Scene) {}

  /** 加载并构建 tilemap / Load and build tilemap with layers */
  build(sceneId: string, extJson: Record<string, any>): void {
    // ── 多 tileset 数组 / Tilesets array ──
    const tilesets: Array<{ name: string; url: string }> = extJson.tilesets || [];
    // 兼容旧格式
    if (tilesets.length === 0 && extJson.tileset_name && extJson.tileset_image_key) {
      tilesets.push({ name: extJson.tileset_name, url: extJson.tileset_image_key });
    }
    const tileSize = extJson.tile_size || 16;

    log.info(`build sceneId=${sceneId} tilesets=%d tile_size=%d`, tilesets.length, tileSize);

    this.tilemap = this.scene.make.tilemap({ key: sceneId });
    if (!this.tilemap) {
      log.error(`tilemap null for key=${sceneId}`);
      return;
    }

    // 添加所有 tileset
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

    if (allTilesets.length === 0) return;

    // ── 动态图层：从 tilemap JSON 自动检测图层名 / Dynamic layer detection ──
    const layerNames: string[] = [];
    for (const ly of (this.tilemap as any).layers || []) {
      if (ly.type === "tilelayer" && ly.name) {
        layerNames.push(ly.name);
      }
    }
    log.info(`  layers: %s`, layerNames.join(", "));

    const hasAbove = layerNames.some(
      (n) => n.toLowerCase().includes("above") || n.toLowerCase() === "overlay"
    );
    const belowLayers = layerNames.filter(
      (n) => !n.toLowerCase().includes("above") && n.toLowerCase() !== "overlay"
    );

    // 底层
    for (const name of belowLayers) {
      const ts = allTilesets[0]; // use first tileset for rendering
      this.tilemap.createLayer(name, ts, 0, 0);
    }

    // 顶层（above player）
    if (hasAbove) {
      const aboveName = layerNames.find(
        (n) => n.toLowerCase().includes("above") || n.toLowerCase() === "overlay"
      );
      if (aboveName) {
        const ts = allTilesets[0];
        const aboveLayer = this.tilemap.createLayer(aboveName, ts, 0, 0);
        if (aboveLayer) aboveLayer.setDepth(DEPTH.ABOVE_PLAYER);
      }
    }

    const mapW = this.tilemap.widthInPixels;
    const mapH = this.tilemap.heightInPixels;
    this.scene.cameras.main.setBounds(0, 0, mapW, mapH);
    log.info(`build OK map=${mapW}x${mapH}px`);
  }

  destroy(): void {
    if (this.tilemap) {
      this.tilemap.destroy();
      this.tilemap = null;
    }
  }
}
