// --- / ---
// -- file start -- / file start
/** 启动场景 / Boot Scene — 动态加载地图资产 */
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
    log.info(
      `world has ${scenes.length} scenes:`,
      scenes.map((s) => `${s.id}(${s.map_key})`).join(", ")
    );

    const loaded = new Set<string>();
    for (const sc of scenes) {
      let ext: any = {};
      try {
        ext = sc.ext_json ? JSON.parse(sc.ext_json) : {};
      } catch {
        log.error(`bad ext_json for ${sc.id}:`, sc.ext_json);
      }
      const tilemapUrl = ext.tilemap_url;
      const tilesetUrl = ext.tileset_url;
      const tilesetImageKey = ext.tileset_image_key;
      const tilesetName = ext.tileset_name;

      log.info(
        `scene ${sc.id}: map_key=${sc.map_key} tilemap=${tilemapUrl} tileset=${tilesetUrl} key=${tilesetImageKey} name=${tilesetName}`
      );

      if (tilesetUrl && !loaded.has(tilesetUrl)) {
        loaded.add(tilesetUrl);
        this.load.image(tilesetImageKey || "tileset", tilesetUrl);
        log.info(`loading image: %s ← %s`, tilesetImageKey, tilesetUrl);
      }
      if (tilemapUrl && sc.map_key) {
        this.load.tilemapTiledJSON(sc.map_key, tilemapUrl);
        log.info(`loading tilemap: %s ← %s`, sc.map_key, tilemapUrl);
      }
    }
  }

  create(): void {
    log.info(`ready, starting Game scene`);
    this.scene.start("Game");
  }
}
