/** 主游戏场景 / Main Game Scene — 数据驱动纹理 + 场景对象渲染 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import type { SceneData } from "../types";

/** 配色规则 / Color rules — 按 race+role 驱动 */
const RACE_SKIN: Record<string, string> = {
  human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574", halfling: "#f5c6a0",
  orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c",
};
const RACE_HAIR: Record<string, string> = {
  human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513", halfling: "#6b3a1f",
  orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00",
};
const ROLE_COLOR: Record<string, string> = {
  fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f",
  ranger: "#27ae60", paladin: "#f1c40f", druid: "#8e44ad", bard: "#e91e63",
  blacksmith: "#a0522d", guard: "#2980b9", merchant: "#16a085",
  innkeeper: "#d35400", quest_giver: "#9b59b6", boss: "#e74c3c",
  villager: "#95a5a6", enemy: "#c0392b",
};

/** 瓦片类型 / Tile types */
enum Tile {
  GRASS = 0, FLOOR = 1, WALL = 2, PATH = 3, WATER = 4,
  DOOR = 5, TREE = 6, SIGN = 7, TORCH = 8, CHEST = 9,
  COUNTER = 10, CARPET = 11,
}
const TILE_COUNT = 12;

export class GameScene extends Phaser.Scene {
  private sprites: Map<string, CharacterSprite> = new Map();
  private tileSize: number = CONFIG.TILE.size;
  private mapLayer!: Phaser.Tilemaps.TilemapLayer | null;
  private sceneObjectIcons: Phaser.GameObjects.Text[] = [];

  constructor() {
    super({ key: "GameScene" });
  }

  preload(): void {
    this.generateTilesetTexture();
  }

  create(): void {
    const state = gameStore.getState();
    this.generateSpriteTextures(state.characters);

    gameStore.subscribe((s) => this.onStateUpdate(s));

    if (state.scenes.length > 0) {
      this.createTileMap(state.scenes[0], state.scene_objects);
      this.updateSprites();
    } else {
      this.add.text(CONFIG.CANVAS.width / 2, CONFIG.CANVAS.height / 2 - 40, "AIGameWorld", {
        fontFamily: "Segoe UI, sans-serif", fontSize: "32px", color: "#ffffff",
      }).setOrigin(0.5).setDepth(100);
    }

    this.events.on("character-clicked", (char: any) => {
      document.dispatchEvent(new CustomEvent("character-selected", { detail: char }));
    });
  }

  /** tileset 纹理 / Tileset texture — 12 种瓦片 */
  private generateTilesetTexture(): void {
    const ts = this.tileSize;
    const w = TILE_COUNT * ts;
    const canvas = this.textures.createCanvas("tileset", w, ts);
    if (!canvas) return;
    const ctx = canvas.context;
    ctx.imageSmoothingEnabled = false;

    const tile = (col: number, bg: string, fg?: string, icon?: string) => {
      const x = col * ts;
      ctx.fillStyle = bg; ctx.fillRect(x + 1, 1, ts - 2, ts - 2);
      if (fg) { ctx.fillStyle = fg; ctx.fillRect(x + 4, 4, ts - 8, ts - 8); } // 内框
      if (icon) { ctx.font = `${ts * 0.6}px serif`; ctx.fillStyle = "#fff"; ctx.fillText(icon, x + ts * 0.2, ts * 0.75); }
      ctx.strokeStyle = "rgba(0,0,0,0.1)"; ctx.lineWidth = 0.5; ctx.strokeRect(x, 0, ts, ts);
    };

    tile(Tile.GRASS, "#2d5a1e", undefined, "🌿");   // 草地
    tile(Tile.FLOOR, "#8b7355", "#7a6245", "🪵");    // 木地板
    tile(Tile.WALL, "#4a4a5a", "#3a3a4a", "🧱");     // 石墙
    tile(Tile.PATH, "#c4a46c", undefined, "🟫");      // 土路
    tile(Tile.WATER, "#1a4a6e", undefined, "🌊");     // 水
    tile(Tile.DOOR, "#6b3a1f", "#4a2a10", "🚪");     // 门
    tile(Tile.TREE, "#1a4a1a", undefined, "🌲");      // 树
    tile(Tile.SIGN, "#8b6914", undefined, "📋");      // 招牌
    tile(Tile.TORCH, "#4a4a5a", undefined, "🔥");     // 火把
    tile(Tile.CHEST, "#8b6914", undefined, "📦");     // 宝箱
    tile(Tile.COUNTER, "#6b4a2a", undefined, "🪑");    // 柜台
    tile(Tile.CARPET, "#8b0000", "#6b0000", "🔴");    // 地毯

    canvas.refresh();
  }

  /** 角色纹理 — 根据实际角色数据动态生成 / Dynamic character textures from data */
  private generateSpriteTextures(characters: Array<{ id: string; race: string | null; role: string; is_pc: boolean; functions?: string[] }>): void {
    const s = this.tileSize;
    for (const ch of characters) {
      if (this.textures.exists(ch.id)) continue; // 已存在 / already cached
      const skin = RACE_SKIN[ch.race || ""] || "#f5cba7";
      const hair = RACE_HAIR[ch.race || ""] || "#4a2c0a";
      const body = ROLE_COLOR[ch.role] || (ch.functions ? ROLE_COLOR[ch.functions[0]] || "#7f8c8d" : "#7f8c8d");

      const canvas = this.textures.createCanvas(ch.id, s, s);
      if (!canvas) continue;
      const ctx = canvas.context;
      ctx.imageSmoothingEnabled = false;
      const cx = s / 2;

      // Body
      ctx.fillStyle = body; ctx.fillRect(cx - 6, 12, 12, 10);
      // Head
      ctx.fillStyle = skin; ctx.beginPath(); ctx.arc(cx, 10, 6, 0, Math.PI * 2); ctx.fill();
      // Hair
      ctx.fillStyle = hair; ctx.beginPath(); ctx.arc(cx, 8, 6, Math.PI, Math.PI * 2); ctx.fill();
      // Eyes
      ctx.fillStyle = "#000"; ctx.fillRect(cx - 3, 9, 2, 2); ctx.fillRect(cx + 1, 9, 2, 2);
      // Legs
      ctx.fillStyle = "#2c3e50"; ctx.fillRect(cx - 5, 22, 4, 6); ctx.fillRect(cx + 1, 22, 4, 6);
      // PC 金边标记 / Gold corner for PC
      if (ch.is_pc) { ctx.fillStyle = "#ffd700"; ctx.fillRect(0, 0, 3, 3); ctx.fillRect(s - 3, 0, 3, 3); }

      canvas.refresh();
    }
  }

  /** 瓦片地图 + 场景对象 / Tile map + scene objects */
  private createTileMap(scene: SceneData, objects: Array<{ id: string; name: string; object_type: string; scene_id: string; position_x: number; position_y: number }>): void {
    const ts = this.tileSize;
    const cols = 30, rows = 20;
    const mapData: number[][] = [];

    for (let r = 0; r < rows; r++) {
      mapData[r] = [];
      for (let c = 0; c < cols; c++) {
        if (r === 0 || r === rows - 1 || c === 0 || c === cols - 1) {
          mapData[r][c] = Tile.WALL;
        } else if ((r + c) % 5 === 0) {
          mapData[r][c] = Tile.PATH;
        } else if ((r + c) % 13 === 3) {
          mapData[r][c] = Tile.TREE;
        } else {
          mapData[r][c] = scene.type === "outdoor" ? Tile.GRASS : Tile.FLOOR;
        }
      }
    }
    // Exits → doors
    for (const exit of scene.exits || []) {
      const ex = Math.min(Math.max(exit.position.x, 0), cols - 1);
      const ey = Math.min(Math.max(exit.position.y, 0), rows - 1);
      mapData[ey]![ex] = Tile.DOOR;
    }
    // Landmarks → special tiles
    for (const lm of scene.landmarks || []) {
      const lx = Math.min(Math.max(lm.position.x, 1), cols - 2);
      const ly = Math.min(Math.max(lm.position.y, 1), rows - 2);
      if (lm.id.includes("tavern")) mapData[ly]![lx] = Tile.SIGN;
      else if (lm.id.includes("blacksmith")) { mapData[ly]![lx] = Tile.TORCH; mapData[ly]![lx + 1] = Tile.COUNTER; }
      else if (lm.id.includes("market")) mapData[ly]![lx] = Tile.CARPET;
    }

    const map = this.make.tilemap({ data: mapData, tileWidth: ts, tileHeight: ts });
    const tileset = map.addTilesetImage("tiles", "tileset", ts, ts, 0, 0);
    if (!tileset) return;
    this.mapLayer = map.createLayer(0, tileset, 0, 0);
    if (!this.mapLayer) return;

    // 场景标题
    const labels: Record<string, string> = { village: "村庄", indoor: "室内", outdoor: "户外", underground: "地下" };
    this.add.text(10, 8, `${scene.name} (${labels[scene.type] || scene.type})`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "13px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 6, y: 2 },
    }).setDepth(50);

    // 地标标签
    for (const lm of scene.landmarks || []) {
      const lx = (lm.position.x % cols) * ts + ts / 2;
      const ly = (lm.position.y % rows) * ts + ts / 2;
      this.add.text(lx, ly + ts / 2 + 2, lm.name, {
        fontFamily: "Segoe UI, sans-serif", fontSize: "10px", color: "#ffd700",
        backgroundColor: "rgba(0,0,0,0.5)", padding: { x: 3, y: 1 },
      }).setOrigin(0.5).setDepth(50);
    }

    // 场景对象图标 / Scene object icons
    this.sceneObjectIcons.forEach(t => t.destroy());
    this.sceneObjectIcons = [];
    const objIcons: Record<string, string> = { container: "📦", door: "🚪", trap: "⚠️", mechanism: "⚙️", decoration: "🏺", item_drop: "💎" };
    for (const obj of objects) {
      if (obj.scene_id !== scene.id) continue;
      const ox = (obj.position_x % cols) * ts + ts / 2;
      const oy = (obj.position_y % rows) * ts + ts / 2;
      const icon = objIcons[obj.object_type] || "❓";
      const t = this.add.text(ox, oy - 4, icon, { fontSize: `${ts * 0.4}px` }).setOrigin(0.5).setDepth(15);
      const label = this.add.text(ox, oy + ts / 2 - 2, obj.name, {
        fontFamily: "Segoe UI, sans-serif", fontSize: "8px", color: "#aaa",
        backgroundColor: "rgba(0,0,0,0.4)", padding: { x: 2, y: 0 },
      }).setOrigin(0.5).setDepth(15);
      this.sceneObjectIcons.push(t, label);
    }
  }

  private onStateUpdate(_s: ReturnType<typeof gameStore.getState>): void {
    this.updateSprites();
  }

  private updateSprites(): void {
    const state = gameStore.getState();
    // 有新角色就生成纹理 / Generate textures for new characters
    this.generateSpriteTextures(state.characters);

    for (const [id, sprite] of this.sprites) {
      if (!state.characters.find(c => c.id === id)) { sprite.destroy(); this.sprites.delete(id); }
    }
    for (const ch of state.characters) {
      const pos = state.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      const ex = this.sprites.get(ch.id);
      if (ex) {
        ex.moveTo(pos.x, pos.y, 300);
        if (ch.combat) ex.updateHp(ch.combat.hp, ch.combat.max_hp);
      } else {
        this.sprites.set(ch.id, new CharacterSprite(this, ch, pos.x, pos.y, this.tileSize));
      }
    }
  }
}
