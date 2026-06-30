/** 主游戏场景 / Main Game Scene — tileset 瓦片地图 + RPG 风格精灵 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import type { SceneData } from "../types";

/** 瓦片类型 / Tile types */
enum Tile {
  GRASS = 0,
  FLOOR = 1,
  WALL = 2,
  PATH = 3,
  WATER = 4,
  DOOR = 5,
}

export class GameScene extends Phaser.Scene {
  private sprites: Map<string, CharacterSprite> = new Map();
  private tileSize: number = CONFIG.TILE.size;
  private mapLayer!: Phaser.Tilemaps.TilemapLayer | null;

  constructor() {
    super({ key: "GameScene" });
  }

  preload(): void {
    this.generateTilesetTexture();
    this.generateSpriteTextures();
  }

  create(): void {
    this.tileSize = CONFIG.TILE.size;

    // 监听状态变化 / Listen to state changes
    gameStore.subscribe((state) => {
      this.onStateUpdate(state);
    });

    // 绘制地图 / Draw map
    const state = gameStore.getState();
    if (state.scenes.length > 0) {
      this.createTileMap(state.scenes[0]);
      this.updateSprites();
    } else {
      // 占位 / Placeholder
      this.add.text(CONFIG.CANVAS.width / 2, CONFIG.CANVAS.height / 2 - 40, "AIGameWorld", {
        fontFamily: "Segoe UI, sans-serif", fontSize: "32px", color: "#ffffff",
      }).setOrigin(0.5).setDepth(100);
      this.add.text(CONFIG.CANVAS.width / 2, CONFIG.CANVAS.height / 2 + 10,
        "aw -i 导入 pack 后刷新页面", {
          fontFamily: "Segoe UI, sans-serif", fontSize: "14px", color: "#8899aa",
        }).setOrigin(0.5).setDepth(100);
    }

    // 监听角色点击 / Listen for character clicks
    this.events.on("character-clicked", (char: any) => {
      document.dispatchEvent(new CustomEvent("character-selected", { detail: char }));
    });
  }

  /** 生成 tileset 纹理 / Generate tileset texture */
  private generateTilesetTexture(): void {
    const ts = this.tileSize;
    const totalCols = 6;
    const canvas = this.textures.createCanvas("tileset", totalCols * ts, ts);
    if (!canvas) return;
    const ctx = canvas.context;
    ctx.imageSmoothingEnabled = false;

    const drawTile = (col: number, base: string, detail: string, dotColor?: string) => {
      const x = col * ts;
      // Background / 背景
      ctx.fillStyle = base;
      ctx.fillRect(x, 0, ts, ts);
      // Detail / 细节
      if (detail) {
        ctx.fillStyle = detail;
        for (let i = 0; i < 3; i++) {
          const rx = x + Math.floor(Math.random() * 999) % (ts - 4) + 2;
          const ry = Math.floor(Math.random() * 999) % (ts - 4) + 2;
          ctx.fillRect(rx, ry, 2, 2);
        }
      }
      // Dot / 点
      if (dotColor) {
        ctx.fillStyle = dotColor;
        ctx.fillRect(x + ts / 2 - 1, ts / 2 - 1, 2, 2);
      }
      // Grid lines / 网格线
      ctx.strokeStyle = "rgba(0,0,0,0.1)";
      ctx.lineWidth = 0.5;
      ctx.strokeRect(x, 0, ts, ts);
    };

    drawTile(Tile.GRASS, "#2d5a1e", "#3a6b28");       // 草地 / Grass
    drawTile(Tile.FLOOR, "#8b7355", "#9c8465");         // 木地板 / Wood floor
    drawTile(Tile.WALL, "#4a4a5a", "#5a5a6a");          // 石墙 / Stone wall
    drawTile(Tile.PATH, "#c4a46c", "#d4b47c");          // 土路 / Dirt path
    drawTile(Tile.WATER, "#1a4a6e", "#2a5a7e");          // 水域 / Water
    drawTile(Tile.DOOR, "#6b3a1f", "#8b4a2f", "#ffd700"); // 门 / Door

    canvas.refresh();
  }

  /** 生成角色纹理 / Generate character sprite textures */
  private generateSpriteTextures(): void {
    const s = this.tileSize;
    const types: Array<{ key: string; body: string; skin: string; hair: string }> = [
      { key: "pc_fighter", body: "#c0392b", skin: "#f5cba7", hair: "#4a2c0a" },
      { key: "pc_rogue", body: "#2c3e50", skin: "#f5cba7", hair: "#1a1a2e" },
      { key: "pc_cleric", body: "#f0f0f0", skin: "#fdebd0", hair: "#d4a574" },
      { key: "pc_wizard", body: "#5b2c6f", skin: "#f5cba7", hair: "#c0c0c0" },
      { key: "actor_default", body: "#7f8c8d", skin: "#f5cba7", hair: "#5d4037" },
    ];

    for (const t of types) {
      const canvas = this.textures.createCanvas(t.key, s, s);
      if (!canvas) continue;
      const ctx = canvas.context;
      ctx.imageSmoothingEnabled = false;
      const cx = s / 2;

      // Body / 身体 (rectangle)
      ctx.fillStyle = t.body;
      ctx.fillRect(cx - 6, 12, 12, 10);

      // Head / 头 (circle)
      ctx.fillStyle = t.skin;
      ctx.beginPath();
      ctx.arc(cx, 10, 6, 0, Math.PI * 2);
      ctx.fill();

      // Hair / 头发
      ctx.fillStyle = t.hair;
      ctx.beginPath();
      ctx.arc(cx, 8, 6, Math.PI, Math.PI * 2);
      ctx.fill();

      // Eyes / 眼睛
      ctx.fillStyle = "#000";
      ctx.fillRect(cx - 3, 9, 2, 2);
      ctx.fillRect(cx + 1, 9, 2, 2);

      // Legs / 腿
      ctx.fillStyle = "#2c3e50";
      ctx.fillRect(cx - 5, 22, 4, 6);
      ctx.fillRect(cx + 1, 22, 4, 6);

      canvas.refresh();
    }
  }

  /** 创建瓦片地图 / Create tile-based map */
  private createTileMap(scene: SceneData): void {
    const ts = this.tileSize;
    const cols = 30;
    const rows = 20;

    // Map data / 地图数据
    const mapData: number[][] = [];
    for (let r = 0; r < rows; r++) {
      mapData[r] = [];
      for (let c = 0; c < cols; c++) {
        if (scene.type === "indoor" || scene.type === "village") {
          // 边框墙 / Border wall
          if (r === 0 || r === rows - 1 || c === 0 || c === cols - 1) {
            mapData[r][c] = Tile.WALL;
          } else if ((r + c) % 5 === 0) {
            mapData[r][c] = Tile.PATH; // 道路 / Path
          } else {
            mapData[r][c] = Tile.FLOOR;
          }
        } else {
          // 户外 / Outdoor
          mapData[r][c] = (r + c) % 3 === 0 ? Tile.GRASS : Tile.PATH;
        }
      }
    }

    // 门 / Doors (at exits)
    for (const exit of scene.exits) {
      const ex = Math.min(Math.max(exit.position.x, 0), cols - 1);
      const ey = Math.min(Math.max(exit.position.y, 0), rows - 1);
      mapData[ey]![ex] = Tile.DOOR;
    }

    // 水 / Water (random patches)
    if (scene.type === "outdoor") {
      mapData[8]![12] = Tile.WATER;
      mapData[8]![13] = Tile.WATER;
      mapData[9]![12] = Tile.WATER;
    }

    // Create map / 创建地图
    const map = this.make.tilemap({
      data: mapData,
      tileWidth: ts,
      tileHeight: ts,
    });

    const tileset = map.addTilesetImage("tiles", "tileset", ts, ts, 0, 0);
    if (!tileset) return;

    this.mapLayer = map.createLayer(0, tileset, 0, 0);
    if (!this.mapLayer) return;

    // Scene title / 场景标题
    const typeLabelMap: Record<string, string> = { village: "村庄", indoor: "室内", outdoor: "户外", underground: "地下" };
    const typeLabel = typeLabelMap[scene.type] || scene.type;
    this.add.text(10, 8, `${scene.name} (${typeLabel})`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "13px",
      color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 6, y: 2 },
    }).setDepth(50).setScrollFactor(0);

    // Landmarks / 地标
    for (const lm of scene.landmarks) {
      const lx = (lm.position.x % cols) * ts + ts / 2;
      const ly = (lm.position.y % rows) * ts + ts / 2;
      this.add.text(lx, ly + ts / 2 + 2, lm.name, {
        fontFamily: "Segoe UI, sans-serif", fontSize: "10px",
        color: "#ffd700", backgroundColor: "rgba(0,0,0,0.5)",
        padding: { x: 3, y: 1 },
      }).setOrigin(0.5).setDepth(50);
    }

    // Description / 描述
    this.add.text(10, rows * ts - 16, scene.description, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "10px",
      color: "rgba(255,255,255,0.5)",
    }).setDepth(50).setScrollFactor(0);
  }

  private onStateUpdate(_state: ReturnType<typeof gameStore.getState>): void {
    this.updateSprites();
  }

  /** 更新所有角色精灵 / Update all character sprites */
  private updateSprites(): void {
    const state = gameStore.getState();
    for (const [id, sprite] of this.sprites) {
      if (!state.characters.find(c => c.id === id)) {
        sprite.destroy();
        this.sprites.delete(id);
      }
    }
    for (const char of state.characters) {
      const pos = state.character_positions[char.id] || { x: char.position_x, y: char.position_y };
      const existing = this.sprites.get(char.id);
      if (existing) {
        existing.moveTo(pos.x, pos.y, 300);
        if (char.combat) existing.updateHp(char.combat.hp, char.combat.max_hp);
      } else {
        const sprite = new CharacterSprite(this, char, pos.x, pos.y, this.tileSize);
        this.sprites.set(char.id, sprite);
      }
    }
  }
}
