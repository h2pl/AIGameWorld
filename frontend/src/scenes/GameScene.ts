/** 主游戏场景 / Main Game Scene — 高质感像素 tileset + 角色精灵 + 场景对象 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import type { SceneData } from "../types";

const RACE_SKIN: Record<string, string> = { human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574", halfling: "#f5c6a0", orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c" };
const RACE_HAIR: Record<string, string> = { human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513", halfling: "#6b3a1f", orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00" };
const ROLE_COLOR: Record<string, string> = { fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f", ranger: "#27ae60", paladin: "#f1c40f", blacksmith: "#a0522d", guard: "#2980b9", merchant: "#16a085", innkeeper: "#d35400", boss: "#e74c3c", enemy: "#c0392b", villager: "#95a5a6" };

/* 24种瓦片 / 24 tile types */
enum T { // 自然类 / Nature
  GRASS, GGRASS, TGRASS, DIRT, SAND, WATER, DEEPW, SHORE,
  // 路径 / Paths
  PATH, BRIDGE,
  // 植被 / Vegetation
  TREE_TL, TREE_TR, TREE_BL, TREE_BR, STUMP, BUSH, FLOWER,
  // 建筑 / Buildings
  WALL, ROOF, DOOR, WINDOW,
  // 装饰 / Decor
  CHEST, BARREL, SIGN,
}
const TC = Object.keys(T).length / 2;

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
    this.events.on("character-clicked", (c: any) => document.dispatchEvent(new CustomEvent("character-selected", { detail: c })));
  }

  /* ═════════════════════ 24种手绘像素瓦片 / 24 hand-pixelled tiles ═════════════════════ */
  private genTileset(): void {
    const s = this.ts, w = TC * s;
    const cv = this.textures.createCanvas("tileset", w, s);
    if (!cv) return;
    const c = cv.context; c.imageSmoothingEnabled = false;
    const P = (x: number, y: number, clr: string) => { c.fillStyle = clr; c.fillRect(x, y, 1, 1); };
    const R = (x: number, y: number, w2: number, h: number, clr: string) => { c.fillStyle = clr; c.fillRect(x, y, w2, h); };
    const t = (col: number, fn: (ox: number) => void) => { fn(col * s); c.strokeStyle = "rgba(0,0,0,0.05)"; c.lineWidth = 0.5; c.strokeRect(col * s, 0, s, s); };

    // ── 自然地面 / Natural Ground ──
    t(T.GRASS, ox => { // 草 - 3层绿
      R(ox, 0, s, s, "#5a9e3a");
      for (let y = 0; y < s; y += 2) for (let x = ox; x < ox + s; x += 2) {
        const r = Math.floor(Math.random() * 99);
        if (r < 25) P(x, y, "#4a8e2a"); else if (r < 40) P(x, y, "#6aae4a"); else if (r < 45) P(x, y, "#3a7e1a");
      }
      // 草叶 / grass blades
      for (let i = 0; i < 6; i++) {
        const bx = ox + 4 + i * 4, by = 2 + (i % 3) * 10;
        P(bx, by, "#7abe5a"); P(bx, by - 1, "#8ace6a"); P(bx + 1, by, "#6aae4a");
      }
    });

    t(T.GGRASS, ox => { // 亮草 / Bright grass
      R(ox, 0, s, s, "#6aae4a");
      for (let i = 0; i < 25; i++) P(ox + 2 + (i * 5) % (s - 4), 2 + i % 8 * 4, "#7abe5a");
      for (let i = 0; i < 15; i++) P(ox + 4 + (i * 7) % (s - 4), 4 + i % 6 * 5, "#5a9e3a");
      for (let i = 0; i < 4; i++) { P(ox + 6 + i * 6, 6, "#8ace6a"); P(ox + 6 + i * 6, 5, "#9ade7a"); }
    });

    t(T.TGRASS, ox => { // 高草 / Tall grass - 更深
      R(ox, 0, s, s, "#4a7e2a");
      for (let y = 0; y < s; y += 3) for (let x = ox; x < ox + s; x += 3) {
        P(x, y, Math.random() > 0.5 ? "#3a6e1a" : "#5a8e3a");
      }
      for (let i = 0; i < 8; i++) { P(ox + 3 + i * 3, i % 2 === 0 ? 3 : 10, "#7aae4a"); P(ox + 3 + i * 3, i % 2 === 0 ? 2 : 9, "#8abe5a"); }
    });

    t(T.DIRT, ox => { // 泥土
      R(ox, 0, s, s, "#b8945c");
      for (let i = 0; i < 30; i++) P(ox + 2 + (i * 7) % (s - 4), 1 + (i * 5) % (s - 2), Math.random() > 0.5 ? "#a8844c" : "#c8a46c");
      // 小石子 / pebbles
      for (let i = 0; i < 4; i++) { P(ox + 5 + i * 7, 4 + i % 3 * 8, "#8a7a6a"); P(ox + 6 + i * 7, 5 + i % 3 * 8, "#9a8a7a"); }
    });

    t(T.SAND, ox => { // 沙地
      R(ox, 0, s, s, "#dcc490");
      for (let i = 0; i < 20; i++) P(ox + 2 + (i * 9) % (s - 4), 2 + (i * 7) % (s - 4), "#ccb480");
      for (let i = 0; i < 10; i++) P(ox + 3 + (i * 11) % (s - 4), 3 + (i * 13) % (s - 4), "#ddcca0");
    });

    t(T.WATER, ox => { // 浅水 - 波光
      R(ox, 0, s, s, "#2a6aaa");
      for (let y = 2; y < s; y += 4) { R(ox + 2 + (y % 2), y, s - 6, 2, "#3a7aba"); P(ox + s / 2 - 2 + (y % 2) * 4, y + 1, "#5a9ada"); }
      for (let i = 0; i < 6; i++) P(ox + 6 + i * 4, 2 + i % 2 * 12, "#4a8aca"); // 高光
    });

    t(T.DEEPW, ox => { // 深水
      R(ox, 0, s, s, "#1a4a7a");
      for (let y = 2; y < s; y += 5) { R(ox + 2 + (y % 3), y, s - 6, 3, "#2a5a8a"); P(ox + s / 2 + (y % 2) * 4, y + 1, "#3a6a9a"); }
    });

    t(T.SHORE, ox => { // 水岸
      R(ox, 0, s, s, "#8a7a5a");
      R(ox, 0, s, 8, "#b8945c"); // 上半部沙 / top sand
      R(ox, 8, s, 4, "#9a8a6a"); // 过渡
      R(ox, 12, s, 20, "#2a6aaa"); // 下半部水 / bottom water
      for (let y = 14; y < s; y += 4) { R(ox + 2, y, s - 6, 2, "#3a7aba"); P(ox + 12, y + 1, "#5a9ada"); }
    });

    // ── 路径 / Paths ──
    t(T.PATH, ox => { // 石板路
      R(ox, 0, s, s, "#7a7a6a");
      for (let y = 1; y < s; y += 8) for (let x = ox + 1; x < ox + s; x += 8) {
        const pw = 6 + ((x + y) % 2), ph = 6 + ((x + y * 2) % 2);
        R(x + ((x + y) % 2), y + ((x * y) % 2), pw, ph, "#8a8a7a");
        R(x + ((x + y) % 2) + 1, y + ((x * y) % 2) + 1, pw - 2, ph - 2, "#9a9a8a");
        c.strokeStyle = "rgba(0,0,0,0.15)"; c.lineWidth = 0.5; c.strokeRect(x + ((x + y) % 2), y + ((x * y) % 2), pw, ph);
      }
    });

    t(T.BRIDGE, ox => { // 木桥
      R(ox, 0, s, s, "#6b4a2a"); // 木底板
      for (let y = 0; y < s; y += 4) { R(ox + 1, y + 1, s - 2, 2, "#7b5a3a"); P(ox + s / 2, y + 1, "#5a3a1a"); }
      R(ox + 1, 0, 2, s, "#4a2a1a"); R(ox + s - 3, 0, 2, s, "#4a2a1a"); // 栏杆
    });

    // ── 植被 / Vegetation ──
    t(T.TREE_TL, ox => { // 树左上
      R(ox, 0, s, s, "#5a9e3a"); // 草背景
      R(ox + 10, 14, 8, 18, "#6b4226"); R(ox + 11, 16, 6, 16, "#7b5236"); // 树干
      // 树冠
      const leaf = ["#1a4a1a", "#2a5a2a", "#1e521e", "#2e622a", "#3a7a3a", "#2a6a2a"];
      for (let dy = 2; dy < 16; dy += 2) for (let dx = ox + 4; dx < ox + 20; dx += 2) {
        const dist = Math.abs(dx - ox - 12) + Math.abs(dy - 8) * 1.2;
        if (dist < 10) P(dx, dy, leaf[Math.floor(Math.random() * leaf.length)]);
      }
      for (let i = 0; i < 5; i++) P(ox + 6 + i * 3, 3, "#5abe5a"); // 高光
    });

    t(T.TREE_TR, ox => { // 树右上
      R(ox, 0, s, s, "#5a9e3a");
      const leaf = ["#1a4a1a", "#2a5a2a", "#1e521e", "#2e622a", "#3a7a3a"];
      for (let dy = 2; dy < 16; dy += 2) for (let dx = ox + 10; dx < ox + 28; dx += 2) {
        const dist = Math.abs(dx - ox - 18) + Math.abs(dy - 8) * 1.2;
        if (dist < 10) P(dx, dy, leaf[Math.floor(Math.random() * leaf.length)]);
      }
    });

    t(T.TREE_BL, ox => { // 树左下
      R(ox, 0, s, s, "#5a9e3a");
      R(ox + 10, 8, 8, 24, "#6b4226"); R(ox + 11, 10, 6, 22, "#7b5236");
      const leaf = ["#1a4a1a", "#2a5a2a", "#3a7a3a", "#2e622a"];
      for (let dy = 4; dy < 20; dy += 2) for (let dx = ox + 4; dx < ox + 20; dx += 2) {
        const dist = Math.abs(dx - ox - 12) + Math.abs(dy - 12) * 1.2;
        if (dist < 10) P(dx, dy, leaf[Math.floor(Math.random() * leaf.length)]);
      }
    });

    t(T.TREE_BR, ox => { // 树右下
      R(ox, 0, s, s, "#5a9e3a");
      const leaf = ["#1a4a1a", "#2a5a2a", "#3a7a3a"];
      for (let dy = 4; dy < 20; dy += 2) for (let dx = ox + 10; dx < ox + 28; dx += 2) {
        const dist = Math.abs(dx - ox - 18) + Math.abs(dy - 12) * 1.2;
        if (dist < 10) P(dx, dy, leaf[Math.floor(Math.random() * leaf.length)]);
      }
    });

    t(T.STUMP, ox => { // 树桩
      R(ox, 0, s, s, "#5a9e3a");
      R(ox + 8, 12, 16, 16, "#6b4226"); R(ox + 10, 10, 12, 4, "#7b5236");
      for (let i = 0; i < 3; i++) P(ox + 10 + i * 4, 10, "#8b6246");
    });

    t(T.BUSH, ox => { // 灌木丛
      R(ox, 0, s, s, "#4a8e2a");
      R(ox + 4, 8, 24, 18, "#2a6a2a"); R(ox + 6, 6, 20, 6, "#3a8a3a");
      for (let i = 0; i < 8; i++) { P(ox + 6 + i * 3, 4, "#5a9a4a"); P(ox + 8 + i * 2, 12, "#1a5a1a"); }
    });

    t(T.FLOWER, ox => { // 花
      R(ox, 0, s, s, "#6aae4a");
      for (let i = 0; i < 5; i++) { P(ox + 6 + i * 5, 2 + i % 2 * 8, "#5a9e3a"); P(ox + 5 + i * 5, 1 + i % 2 * 8, "#8ace6a"); }
      // 花朵
      P(ox + 10, 8, "#ff6688"); P(ox + 9, 7, "#ff4477"); P(ox + 11, 7, "#ff4477"); P(ox + 10, 9, "#ff88aa");
      P(ox + 20, 16, "#ffaa00"); P(ox + 19, 15, "#ff8800"); P(ox + 21, 15, "#ffcc00");
    });

    // ── 建筑 / Buildings ──
    t(T.WALL, ox => { // 石墙（带砖缝）
      R(ox, 0, s, s, "#6a6a6a");
      for (let y = 0; y < s; y += 6) for (let x = ox; x < ox + s; x += 8) {
        const off = (Math.floor(y / 6) % 2) * 4;
        R(x + off, y, 7, 5, "#7a7a7a"); R(x + off + 1, y + 1, 5, 3, "#8a8a8a");
        P(x + off + 2, y + 2, "#9a9a9a"); // 高光
        c.strokeStyle = "rgba(0,0,0,0.3)"; c.lineWidth = 0.5; c.strokeRect(x + off, y, 7, 5);
      }
    });

    t(T.ROOF, ox => { // 红瓦屋顶
      R(ox, 0, s, s, "#8b2500");
      for (let y = 0; y < s; y += 4) for (let x = ox + (y % 2); x < ox + s; x += 8) {
        R(x, y, 7, 3, "#a03500"); R(x + 1, y + 1, 5, 2, "#b04500");
        P(x + 2, y + 1, "#c05500"); // 高光
      }
      R(ox + 1, 2, s - 2, 2, "#c05500"); // 屋脊
    });

    t(T.DOOR, ox => { // 木门
      R(ox, 0, s, s, "#6a6a6a");
      R(ox + 6, 0, 20, 30, "#5a3a1a"); R(ox + 8, 2, 16, 26, "#6b4a2a");
      R(ox + 10, 4, 12, 22, "#7b5a3a");
      P(ox + 18, 12, "#ffd700"); P(ox + 18, 13, "#ffd700"); // 门把手
      R(ox + 10, 6, 12, 4, "#8b6a4a"); // 门板上横
      R(ox + 10, 18, 12, 4, "#8b6a4a"); // 门板下横
    });

    t(T.WINDOW, ox => { // 窗户
      R(ox, 0, s, s, "#6a6a6a");
      R(ox + 6, 6, 20, 18, "#3a6a9a"); // 玻璃
      R(ox + 7, 7, 18, 16, "#5a9aca");
      P(ox + 14, 10, "#8acefa"); P(ox + 14, 16, "#8acefa"); // 反光
      R(ox + 6, 14, 20, 2, "#4a3a2a"); // 横窗框
      R(ox + 14, 6, 2, 18, "#4a3a2a"); // 竖窗框
    });

    // ── 装饰 / Decor ──
    t(T.CHEST, ox => { // 宝箱
      R(ox, 0, s, s, "#5a9e3a");
      R(ox + 4, 12, 24, 18, "#8b4513"); R(ox + 6, 10, 20, 6, "#a0522d");
      R(ox + 4, 24, 6, 6, "#7a3520"); R(ox + 22, 24, 6, 6, "#7a3520"); //脚
      R(ox + 14, 10, 4, 4, "#ffd700"); // 锁
    });

    t(T.BARREL, ox => { // 木桶
      R(ox, 0, s, s, "#5a9e3a");
      R(ox + 6, 6, 20, 22, "#8b4513"); R(ox + 8, 8, 16, 18, "#a0522d");
      for (let y = 12; y < 24; y += 5) { R(ox + 6, y, 20, 2, "#7a3520"); P(ox + 8, y + 1, "#b0623d"); }
      R(ox + 12, 4, 8, 4, "#a0522d"); // 桶顶
    });

    t(T.SIGN, ox => { // 招牌
      R(ox, 0, s, s, "#5a9e3a");
      R(ox + 14, 6, 4, 24, "#6b4226"); // 杆
      R(ox + 4, 2, 24, 10, "#8b6914"); // 牌
      R(ox + 6, 4, 20, 6, "#a07924");
      P(ox + 16, 6, "#8a6a2a"); // 钉子
    });

    cv.refresh();
  }

  /* ═════════════════════ 角色精灵 / Character sprites ═════════════════════ */
  private genSprites(chars: Array<{ id: string; race: string | null; role: string; is_pc: boolean; functions?: string[] }>): void {
    const s = this.ts;
    for (const ch of chars) {
      if (this.textures.exists(ch.id)) continue;
      const skin = RACE_SKIN[ch.race || ""] || "#f5cba7";
      const hair = RACE_HAIR[ch.race || ""] || "#4a2c0a";
      const body = ROLE_COLOR[ch.role] || (ch.functions?.[0] ? ROLE_COLOR[ch.functions[0]] || "#7f8c8d" : "#7f8c8d");
      const cv = this.textures.createCanvas(ch.id, s, s);
      if (!cv) continue;
      const c = cv.context; c.imageSmoothingEnabled = false;
      const cx = s / 2;
      c.fillStyle = body; c.fillRect(cx - 6, 11, 12, 10);           // 身体
      c.fillStyle = skin; c.beginPath(); c.arc(cx, 10, 6, 0, Math.PI * 2); c.fill(); // 头
      c.fillStyle = hair; c.beginPath(); c.arc(cx, 8, 6, Math.PI, Math.PI * 2); c.fill(); // 发
      c.fillStyle = "#000"; c.fillRect(cx - 3, 9, 2, 2); c.fillRect(cx + 1, 9, 2, 2); // 眼
      c.fillStyle = "#2c3e50"; c.fillRect(cx - 5, 21, 4, 7); c.fillRect(cx + 1, 21, 4, 7); // 腿
      if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 8, 12, 3, 4); c.fillRect(cx + 5, 12, 3, 4); } // 金肩章
      cv.refresh();
    }
  }

  /* ═════════════════════ 地图构建 / Map building ═════════════════════ */
  private buildMap(scene: SceneData, objs: Array<{ id: string; name: string; object_type: string; scene_id: string; position_x: number; position_y: number }>): void {
    const s = this.ts, C = 30, R = 20;
    const map: number[][] = [];
    const isOut = scene.type === "outdoor";
    for (let r = 0; r < R; r++) { map[r] = []; for (let c = 0; c < C; c++) map[r][c] = isOut ? T.GGRASS : T.GRASS; }

    // 水域 / Water patches
    if (isOut) {
      for (let r = 6; r < 10; r++) for (let c = 20; c < 25; c++) map[r][c] = T.WATER;
      for (let r = 14; r < 16; r++) for (let c = 4; c < 8; c++) map[r][c] = T.DEEPW;
    }
    // 路径 / Paths
    for (let i = 0; i < C; i++) { map[4]![i] = T.DIRT; map[10]![i] = T.PATH; }
    for (let i = 0; i < R; i++) { map[i]![8] = T.PATH; map[i]![18] = T.DIRT; }
    // 树木 / Trees (成片放置)
    for (let r = 2; r < 4; r++) for (let c = 2; c < 5; c++) map[r][c] = c % 2 === 0 ? T.TREE_TL : T.TREE_TR;
    for (let r = 12; r < 14; r++) for (let c = 22; c < 25; c++) map[r][c] = c % 2 === 0 ? T.TREE_BL : T.TREE_BR;
    for (let r = 15; r < 18; r++) for (let c = 1; c < 3; c++) map[r][c] = r % 2 === 0 ? T.TREE_TL : T.TREE_TR;
    // 灌木 / Bushes
    for (let i = 0; i < 6; i++) map[1 + i]![12 + i] = T.BUSH;
    for (let i = 0; i < 4; i++) map[15]![10 + i * 2] = T.BUSH;
    // 花 / Flowers
    for (let i = 0; i < 4; i++) map[6 + i]![22] = T.FLOWER;
    // 树桩 / Stumps
    map[7]![14] = T.STUMP; map[13]![6] = T.STUMP;
    // 建筑 / Buildings (左下角)
    for (let r = 16; r < R; r++) for (let c = 20; c < 28; c++) map[r][c] = r === 16 ? T.ROOF : T.WALL;
    map[16]![24] = T.DOOR; map[18]![22] = T.WINDOW; map[18]![26] = T.WINDOW;

    // 出口 → 沙地标记
    for (const ex of scene.exits || []) { map[Math.min(ex.position.y, R - 1)]![Math.min(ex.position.x, C - 1)] = T.SAND; map[Math.min(ex.position.y + 1, R - 1)]![Math.min(ex.position.x, C - 1)] = T.SAND; }

    // 地标 → 特殊装饰
    for (const lm of scene.landmarks || []) {
      const lc = Math.min(Math.max(lm.position.x, 1), C - 2), lr = Math.min(Math.max(lm.position.y, 1), R - 2);
      if (lm.id.includes("tavern")) { map[lr]![lc] = T.SIGN; map[lr]![lc + 1] = T.BARREL; }
      else if (lm.id.includes("blacksmith")) { map[lr]![lc] = T.SIGN; }
      else if (lm.id.includes("market")) { map[lr]![lc] = T.SIGN; map[lr]![lc + 1] = T.CHEST; }
    }

    const tilemap = this.make.tilemap({ data: map, tileWidth: s, tileHeight: s });
    const tileset = tilemap.addTilesetImage("tiles", "tileset", s, s, 0, 0);
    if (!tileset) return;
    tilemap.createLayer(0, tileset, 0, 0);

    // HUD
    const labels: Record<string, string> = { village: "村庄", indoor: "室内", outdoor: "野外", underground: "地下" };
    this.add.text(10, 4, `${scene.name} (${labels[scene.type] || scene.type})`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setDepth(50);

    // 地标标签
    for (const lm of scene.landmarks || []) {
      this.add.text((lm.position.x % C) * s + s / 2, (lm.position.y % R) * s + s / 2 + 14, lm.name, {
        fontSize: "9px", color: "#ffd700", backgroundColor: "rgba(0,0,0,0.5)", padding: { x: 2, y: 1 },
      }).setOrigin(0.5).setDepth(50);
    }
    // 场景对象图标
    this.iconTexts.forEach(t => t.destroy()); this.iconTexts = [];
    const icons: Record<string, string> = { container: "📦", door: "🚪", trap: "⚠", mechanism: "⚙", decoration: "🏺", item_drop: "✦" };
    for (const obj of objs) {
      if (obj.scene_id !== scene.id) continue;
      const t2 = this.add.text((obj.position_x % C) * s + s / 2, (obj.position_y % R) * s + s / 2 - 4, icons[obj.object_type] || "❓", { fontSize: `${s * 0.4}px` }).setOrigin(0.5).setDepth(15);
      this.iconTexts.push(t2);
    }
  }

  /* ═════════════════════ Update ═════════════════════ */
  private onUpdate(st: ReturnType<typeof gameStore.getState>): void {
    this.genSprites(st.characters);
    for (const [id, sp] of this.sprites) { if (!st.characters.find(c => c.id === id)) { sp.destroy(); this.sprites.delete(id); } }
    for (const ch of st.characters) {
      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      const ex = this.sprites.get(ch.id);
      if (ex) { ex.moveTo(p.x, p.y, 300); if (ch.combat) ex.updateHp(ch.combat.hp, ch.combat.max_hp); }
      else this.sprites.set(ch.id, new CharacterSprite(this, ch, p.x, p.y, this.ts));
    }
  }
}
