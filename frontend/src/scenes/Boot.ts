// --- / ---
// -- file start -- / file start
/** 启动场景 / Boot Scene — 动态加载地图资产（支持多 tileset） */
import Phaser from "phaser";
import { sceneList } from "../state/SceneList";
import { createLogger } from "../utils/logger";
const log = createLogger("Boot");

export class Boot extends Phaser.Scene {
  constructor() {
    super({ key: "Boot" });
  }

  preload(): void {
    this.load.on("fileerror", (key: string) => log.error(`load FAIL: %s`, key));
    this.load.on("complete", () => log.info(`all assets loaded`));

    const scenes = sceneList as any[];
    log.info(`world has ${scenes.length} scenes:`, scenes.map((s) => s.id).join(", "));

    const loaded = new Set<string>();
    for (const sc of scenes) {
      let ext: any = {};
      try {
        ext = sc.ext_json ? JSON.parse(sc.ext_json) : {};
      } catch {
        log.error(`bad ext_json for ${sc.id}:`, sc.ext_json);
      }

      // ── 新格式：tilesets 数组 + tile_size / New format: tilesets array ──
      const tilesets: Array<{ name: string; url: string }> = ext.tilesets || [];
      const tilemapUrl = ext.tilemap_url;

      // ── 兼容旧格式：单 tileset / Compat: old single-tileset format ──
      if (tilesets.length === 0 && ext.tileset_url && ext.tileset_image_key && ext.tileset_name) {
        tilesets.push({
          name: ext.tileset_name,
          url: ext.tileset_url,
        });
      }

      // 加载所有 tileset PNG
      for (const ts of tilesets) {
        if (!loaded.has(ts.url)) {
          loaded.add(ts.url);
          this.load.image(ts.name, ts.url);
          log.info(`loading tileset: %s ← %s`, ts.name, ts.url);
        }
      }

      // 加载 tilemap JSON
      if (tilemapUrl) {
        this.load.tilemapTiledJSON(sc.id, tilemapUrl);
        log.info(`loading tilemap: %s ← %s`, sc.id, tilemapUrl);
      }
    }
  }

  create(): void {
    log.info(`ready, starting Game scene`);
    this.scene.start("Game");
  }
}
