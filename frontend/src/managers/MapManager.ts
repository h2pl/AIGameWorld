/** 地图管理器 / Map Manager — 加载 tilemap + 创建图层 + 碰撞 */
import Phaser from "phaser";
import { DEPTH, TILEMAP } from "../constants";
import { createLogger } from "../utils/logger";
const log = createLogger("MapManager");

export class MapManager {
  tilemap: Phaser.Tilemaps.Tilemap | null = null;

  constructor(private scene: Phaser.Scene) {}

  /** 加载并构建 tilemap / Load and build tilemap with layers */
  build(mapKey: string, extJson: Record<string, string>): void {
    const { tileset_name, tileset_image_key } = extJson;
    log.info(`build mapKey=${mapKey} tileset=${tileset_name}/${tileset_image_key}`);
    this.tilemap = this.scene.make.tilemap({ key: mapKey });
    if (!this.tilemap) { log.error(`tilemap null for key=${mapKey}`); return; }
    log.info(`tilemap loaded`);

    const tileset = this.tilemap.addTilesetImage(tileset_name, tileset_image_key);
    if (!tileset) {
      log.error(`tileset FAIL: ${tileset_name}/${tileset_image_key} — available textures:`);
      this.scene.textures.getTextureKeys().forEach(k => log.error(`  texture: ${k}`));
      return;
    }
    log.info(`tileset OK`);

    this.tilemap.createLayer(TILEMAP.LAYERS.BELOW, tileset, 0, 0);
    const worldLayer = this.tilemap.createLayer(TILEMAP.LAYERS.WORLD, tileset, 0, 0);
    if (worldLayer) worldLayer.setCollisionByProperty({ collides: true });
    const aboveLayer = this.tilemap.createLayer(TILEMAP.LAYERS.ABOVE, tileset, 0, 0);
    if (aboveLayer) aboveLayer.setDepth(DEPTH.ABOVE_PLAYER);

    const mapW = this.tilemap.widthInPixels;
    const mapH = this.tilemap.heightInPixels;
    this.scene.cameras.main.setBounds(0, 0, mapW, mapH);
    log.info(`build OK map=${mapW}x${mapH}px`);
  }

  destroy(): void {
    if (this.tilemap) { this.tilemap.destroy(); this.tilemap = null; }
  }
}
