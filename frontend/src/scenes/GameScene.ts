/** 主游戏场景 / Main Game Scene — 像素风 tileset + 数据驱动精灵 + 场景对象 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import type { SceneData } from "../types";

// ── 配色规则 / Color rules ──
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
  innkeeper: "#d35400", quest_giver: "#9b59b6", boss: "#e74c3c", enemy: "#c0392b",
  villager: "#95a5a6",
};

// ── 瓦片 / Tiles ──
enum T {
  GRASS, DIRT, PATH, FLOOR, WOOD, WALL, WATER, DOOR,
  TREE1, TREE2, BUSH, ROCK, CHEST, SIGN, COUNTER, TORCH,
}
const TC = Object.keys(T).length / 2; // 瓦片数量

export class GameScene extends Phaser.Scene {
  private sprites: Map<string, CharacterSprite> = new Map();
  private ts = CONFIG.TILE.size;
  private iconTexts: Phaser.GameObjects.Text[] = [];

  constructor() { super({ key: "GameScene" }); }

  preload(): void { this.genTileset(); }

  create(): void {
    const st = gameStore.getState();
    this.genSprites(st.characters);
    gameStore.subscribe(s => this.onUpdate(s));
    if (st.scenes.length > 0) this.buildMap(st.scenes[0], st.scene_objects);
    this.events.on("character-clicked", (c: any) =>
      document.dispatchEvent(new CustomEvent("character-selected", { detail: c })));
  }

  // ═══ 像素 tileset 生成 / Pixel tileset generation ═══
  private genTileset(): void {
    const s = this.ts, w = TC * s;
    const cv = this.textures.createCanvas("tileset", w, s);
    if (!cv) return;
    const c = cv.context;
    c.imageSmoothingEnabled = false;

    // 工具函数 / helpers
    const pixel = (x: number, y: number, color: string) => { c.fillStyle = color; c.fillRect(x, y, 1, 1); };
    const rect = (x: number, y: number, w2: number, h: number, color: string) => { c.fillStyle = color; c.fillRect(x, y, w2, h); };
    const grid = (col: number) => { c.strokeStyle = "rgba(0,0,0,0.08)"; c.lineWidth = 0.5; c.strokeRect(col * s, 0, s, s); };

    // 草地 / Grass — 绿色基底 + 随机点缀
    const grass = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#3a7d28");
      for (let y = 2; y < s - 2; y += 2) for (let x = ox + 2; x < ox + s - 2; x += 3) {
        const r = Math.floor(Math.random() * 99);
        if (r < 30) pixel(x, y, "#2e6b1e");
        else if (r < 50) pixel(x, y, "#4a8d35");
        else if (r < 55) pixel(x, y + 1, "#5a9d45");
      }
      // 小草叶 / grass blades
      pixel(ox + 4, 3, "#5a9d45"); pixel(ox + 4, 2, "#6aad55");
      pixel(ox + 12, 6, "#5a9d45"); pixel(ox + 12, 5, "#6aad55");
      grid(col);
    };

    // 土路 / Dirt
    const dirt = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#c4a46c");
      for (let i = 0; i < 20; i++) {
        const rx = ox + 2 + (Math.floor(Math.random() * 99) % (s - 4));
        const ry = 2 + (Math.floor(Math.random() * 99) % (s - 4));
        pixel(rx, ry, Math.random() > 0.5 ? "#b8945c" : "#d4b47c");
      }
      grid(col);
    };

    // 石板路 / Path (stone)
    const path = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#8a8a7a");
      for (let y = 1; y < s; y += 8) for (let x = ox + 1; x < ox + s; x += 8) {
        rect(x, y, 6, 6, "#9a9a8a");
        rect(x + 1, y + 1, 4, 4, "#aaaa9a");
        c.strokeStyle = "rgba(0,0,0,0.2)"; c.lineWidth = 0.5;
        c.strokeRect(x, y, 6, 6);
      }
      grid(col);
    };

    // 木地板 / Wood floor
    const floor = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#6b4a2a");
      for (let y = 0; y < s; y += 5) {
        const shade = y % 10 === 0 ? "#7b5a3a" : "#6b4a2a";
        rect(ox + 1, y + 1, s - 2, 3, shade);
        for (let x = ox + 3; x < ox + s - 3; x += 12) pixel(x, y + 2, "#5a3a1a");
      }
      grid(col);
    };

    // 木墙 / Wood wall
    const wood = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#4a3020");
      for (let y = 0; y < s; y += 4) {
        rect(ox + 1, y + 1, s - 2, 2, "#5a4030");
        pixel(ox + s / 2, y + 1, "#3a2010");
      }
      grid(col);
    };

    // 石墙 / Stone wall
    const wall = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#5a5a6a");
      for (let y = 1; y < s; y += 6) for (let x = ox + 1; x < ox + s; x += 8) {
        const w2 = 6 + ((x + y) % 3), h2 = 4 + ((x + y) % 2);
        rect(x + ((x + y) % 2), y + ((x * y) % 2), w2, h2, "#6a6a7a");
        c.strokeStyle = "rgba(0,0,0,0.25)"; c.lineWidth = 0.5;
        c.strokeRect(x + ((x + y) % 2), y + ((x * y) % 2), w2, h2);
        if ((x + y) % 7 === 0) pixel(x + 2, y + 3, "#4a4a5a");
      }
      grid(col);
    };

    // 水 / Water
    const water = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#1a4a7a");
      for (let y = 2; y < s - 2; y += 4) {
        const offset = (y / 4) % 2 === 0 ? 0 : 2;
        rect(ox + 2 + offset, y, s - 6, 2, "#2a5a8a");
        pixel(ox + s / 2 + offset, y + 1, "#4a7aaa");
      }
      grid(col);
    };

    // 门 / Door
    const door = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#4a2a10");
      rect(ox + 8, 0, 16, 28, "#6b3a1f");
      rect(ox + 10, 2, 12, 24, "#8b4a2f");
      rect(ox + 12, 6, 8, 2, "#ffd700"); // 门把手
      rect(ox + 12, 20, 6, 2, "#ffd700");
      rect(ox + 2, 0, 4, s, "#5a5a6a");   // 门框
      rect(ox + s - 6, 0, 4, s, "#5a5a6a");
      grid(col);
    };

    // 树 / Tree
    const tree = (col: number, variant: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#3a7d28"); // 草地背景
      // 树干
      rect(ox + s / 2 - 3, s / 2, 6, s / 2 - 2, "#6b4226");
      rect(ox + s / 2 - 2, s / 2 + 2, 4, s / 2 - 4, "#7b5236");
      // 树冠
      const leafColors = ["#1a5a1a", "#2a6a2a", "#1e5e1e", "#2e6e2e"];
      for (let dy = 2; dy < s / 2 + 4; dy += 2) {
        const rw = (s / 2 - 4) - Math.abs(dy - s / 4) * 0.8;
        for (let dx = -rw; dx <= rw; dx += 2) {
          const lx = ox + s / 2 + dx;
          const ly = dy;
          const ci = Math.floor(Math.random() * leafColors.length);
          rect(lx, ly, 2, 2, leafColors[ci]);
        }
      }
      grid(col);
    };

    // 灌木 / Bush
    const bush = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#3a7d28");
      rect(ox + 6, 4, 20, 20, "#2a6a2a");
      rect(ox + 4, 6, 24, 16, "#3a8a3a");
      for (let i = 0; i < 8; i++) {
        pixel(ox + 8 + i * 2, 8, "#4a9a4a");
      }
      grid(col);
    };

    // 岩石 / Rock
    const rock = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#3a7d28");
      rect(ox + 4, 10, 22, 16, "#7a7a7a");
      rect(ox + 6, 8, 18, 4, "#8a8a8a");
      rect(ox + 8, 6, 14, 4, "#9a9a9a");
      pixel(ox + 10, 12, "#6a6a6a");
      pixel(ox + 16, 14, "#6a6a6a");
      grid(col);
    };

    // 宝箱 / Chest
    const chest = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#8b7355");
      rect(ox + 4, 16, 24, 14, "#a0522d");
      rect(ox + 6, 14, 20, 4, "#c0723d");
      rect(ox + 14, 14, 4, 4, "#ffd700");   // 锁扣 / Lock buckle
      rect(ox + 6, 18, 20, 4, "#8b4513");
      rect(ox + 4, 24, 6, 6, "#7a3520");    // 左腿 / Left leg
      rect(ox + 22, 24, 6, 6, "#7a3520");    // 右腿 / Right leg
      grid(col);
    };

    // 招牌 / Sign
    const sign = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#8b7355");
      rect(ox + 14, 6, 4, 24, "#6b4226"); // 杆
      rect(ox + 6, 4, 20, 8, "#8b6914");  // 牌
      rect(ox + 8, 6, 16, 4, "#a07924");
      grid(col);
    };

    // 柜台 / Counter
    const counter = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#6b4a2a");
      rect(ox + 2, 14, 28, 16, "#8b5a3a");
      rect(ox + 2, 12, 28, 4, "#a06a4a");
      for (let x = ox + 4; x < ox + s - 4; x += 6) pixel(x, 20, "#7a4a2a");
      grid(col);
    };

    // 火把 / Torch
    const torch = (col: number) => {
      const ox = col * s;
      rect(ox, 0, s, s, "#5a5a6a");
      rect(ox + 14, 8, 4, 20, "#6b4226");
      rect(ox + 14, 4, 4, 6, "#8b4513");
      rect(ox + 13, 2, 6, 4, "#ff6600");
      rect(ox + 14, 0, 4, 4, "#ffaa00");
      pixel(ox + 15, 1, "#ffff00");
      grid(col);
    };

    // 绘制 / Draw all
    grass(T.GRASS); dirt(T.DIRT); path(T.PATH);
    floor(T.FLOOR); wood(T.WOOD); wall(T.WALL); water(T.WATER); door(T.DOOR);
    tree(T.TREE1, 1); tree(T.TREE2, 2); bush(T.BUSH); rock(T.ROCK);
    chest(T.CHEST); sign(T.SIGN); counter(T.COUNTER); torch(T.TORCH);
    cv.refresh();
  }

  // ═══ 角色纹理生成 / Sprite generation ═══
  private genSprites(chars: Array<{ id: string; race: string | null; role: string; is_pc: boolean; functions?: string[] }>): void {
    const s = this.ts;
    for (const ch of chars) {
      if (this.textures.exists(ch.id)) continue;
      const skin = RACE_SKIN[ch.race || ""] || "#f5cba7";
      const hair = RACE_HAIR[ch.race || ""] || "#4a2c0a";
      const body = ROLE_COLOR[ch.role] || (ch.functions ? ROLE_COLOR[ch.functions[0]] || "#7f8c8d" : "#7f8c8d");

      const cv = this.textures.createCanvas(ch.id, s, s);
      if (!cv) continue;
      const c = cv.context;
      c.imageSmoothingEnabled = false;
      const cx = s / 2;

      // 身体
      c.fillStyle = body; c.fillRect(cx - 6, 11, 12, 10);
      // 头
      c.fillStyle = skin; c.beginPath(); c.arc(cx, 10, 6, 0, Math.PI * 2); c.fill();
      // 头发
      c.fillStyle = hair; c.beginPath(); c.arc(cx, 8, 6, Math.PI, Math.PI * 2); c.fill();
      // 眼睛
      c.fillStyle = "#000"; c.fillRect(cx - 3, 9, 2, 2); c.fillRect(cx + 1, 9, 2, 2);
      // 腿
      c.fillStyle = "#2c3e50"; c.fillRect(cx - 5, 21, 4, 7); c.fillRect(cx + 1, 21, 4, 7);
      // PC 肩章 / Gold epaulette for PC
      if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 8, 12, 3, 4); c.fillRect(cx + 5, 12, 3, 4); }
      cv.refresh();
    }
  }

  // ═══ 地图构建 / Map building ═══
  private buildMap(scene: SceneData, objs: Array<{ id: string; name: string; object_type: string; scene_id: string; position_x: number; position_y: number }>): void {
    const s = this.ts, C = 30, R = 20;
    const map: number[][] = [];
    const isVillage = scene.type === "village";

    for (let r = 0; r < R; r++) {
      map[r] = [];
      for (let c = 0; c < C; c++) {
        if (r === 0 || r === R - 1 || c === 0 || c === C - 1) map[r][c] = isVillage ? T.WALL : T.WALL;
        else if ((r + c) % 5 === 0 && r > 1 && r < R - 2) map[r][c] = T.PATH;
        else if ((r * c) % 17 === 3 && r > 2 && r < R - 3) map[r][c] = T.BUSH;
        else if ((r * c) % 23 === 7 && r > 3 && r < R - 4) map[r][c] = T.ROCK;
        else if ((r + c) % 11 === 1 && r > 1 && r < R - 2 && c > 1 && c < C - 2) map[r][c] = Math.random() > 0.5 ? T.TREE1 : T.TREE2;
        else map[r][c] = scene.type === "outdoor" ? T.GRASS : T.FLOOR;
      }
    }

    // 出口 → 门 / Exits → doors
    for (const ex of scene.exits || []) {
      const ec = Math.min(Math.max(ex.position.x, 1), C - 2);
      const er = Math.min(Math.max(ex.position.y, 1), R - 2);
      map[er]![ec] = T.DOOR;
    }

    // 地标 → 特殊纹理 / Landmarks → special textures
    for (const lm of scene.landmarks || []) {
      const lc = Math.min(Math.max(lm.position.x, 1), C - 2);
      const lr = Math.min(Math.max(lm.position.y, 1), R - 2);
      if (lm.id.includes("tavern")) { map[lr]![lc] = T.SIGN; map[lr]![lc + 1] = T.COUNTER; }
      else if (lm.id.includes("blacksmith")) { map[lr]![lc] = T.TORCH; map[lr]![lc + 1] = T.COUNTER; }
      else if (lm.id.includes("market")) { map[lr]![lc] = T.SIGN; map[lr]![lc + 1] = T.COUNTER; }
    }

    const tilemap = this.make.tilemap({ data: map, tileWidth: s, tileHeight: s });
    const tileset = tilemap.addTilesetImage("tiles", "tileset", s, s, 0, 0);
    if (!tileset) return;
    tilemap.createLayer(0, tileset, 0, 0);

    // 标题
    const labels: Record<string, string> = { village: "村庄", indoor: "室内", outdoor: "野外", underground: "地下" };
    this.add.text(10, 6, `${scene.name} (${labels[scene.type] || scene.type})`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setDepth(50);

    // 地标标签
    for (const lm of scene.landmarks || []) {
      const lx = (lm.position.x % C) * s + s / 2;
      const ly = (lm.position.y % R) * s + s / 2 + s / 2 + 6;
      this.add.text(lx, ly, lm.name, {
        fontSize: "9px", color: "#ffd700", backgroundColor: "rgba(0,0,0,0.5)", padding: { x: 2, y: 1 },
      }).setOrigin(0.5).setDepth(50);
    }

    // 场景对象图标 / Icons
    this.iconTexts.forEach(t => t.destroy());
    this.iconTexts = [];
    const icons: Record<string, string> = { container: "📦", door: "🚪", trap: "⚠", mechanism: "⚙", decoration: "🏺", item_drop: "✦" };
    for (const obj of objs) {
      if (obj.scene_id !== scene.id) continue;
      const ox = (obj.position_x % C) * s + s / 2;
      const oy = (obj.position_y % R) * s + s / 2 - 4;
      const t = this.add.text(ox, oy, icons[obj.object_type] || "❓", { fontSize: `${s * 0.45}px` }).setOrigin(0.5).setDepth(15);
      this.iconTexts.push(t);
    }
  }

  // ═══ 更新 / Update ═══
  private onUpdate(st: ReturnType<typeof gameStore.getState>): void {
    this.genSprites(st.characters);
    for (const [id, sp] of this.sprites) {
      if (!st.characters.find(c => c.id === id)) { sp.destroy(); this.sprites.delete(id); }
    }
    for (const ch of st.characters) {
      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      const ex = this.sprites.get(ch.id);
      if (ex) { ex.moveTo(p.x, p.y, 300); if (ch.combat) ex.updateHp(ch.combat.hp, ch.combat.max_hp); }
      else this.sprites.set(ch.id, new CharacterSprite(this, ch, p.x, p.y, this.ts));
    }
  }
}
