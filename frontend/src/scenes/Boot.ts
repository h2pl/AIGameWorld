/** 启动场景 / Boot Scene — 加载所有资源，和 phaser-rpg 保持一致 */
import Phaser from "phaser";
import { KEY } from "../constants";

export class Boot extends Phaser.Scene {
  constructor() {
    super({ key: "Boot" });
  }

  preload(): void {
    // Tileset 图片 / Tileset image
    this.load.image(KEY.IMAGE.TUXEMON, "/assets/rpg_tileset.png");
    // Tiled 地图 JSON / Tiled map JSON
    this.load.tilemapTiledJSON(KEY.TILEMAP.TUXEMON, "/assets/tuxemon-town.json");
  }

  create(): void {
    this.scene.start("Game");
  }
}
