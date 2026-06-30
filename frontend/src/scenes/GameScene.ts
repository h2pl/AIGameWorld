/** 主游戏场景 / Main Game Scene — 使用 Tuxemon tileset + 数据驱动精灵 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import type { SceneData } from "../types";

const RACE_SKIN: Record<string, string> = { human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574", halfling: "#f5c6a0", orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c" };
const RACE_HAIR: Record<string, string> = { human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513", halfling: "#6b3a1f", orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00" };
const ROLE_COLOR: Record<string, string> = { fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f", ranger: "#27ae60", paladin: "#f1c40f", blacksmith: "#a0522d", guard: "#2980b9", merchant: "#16a085", innkeeper: "#d35400", boss: "#e74c3c", enemy: "#c0392b", villager: "#95a5a6" };

/* Tuxemon tileset 常用瓦片索引 (0-indexed) / Common tile indices */
const TG: Record<string, number[]> = {
  GRASS: [0, 1, 2, 3, 24, 25, 26, 27],
  DIRT: [48, 49, 50, 51, 72, 73, 74, 75],
  WATER: [192, 193, 194, 195, 216, 217, 218, 219],
  PATH: [144, 145, 146, 147],
  TREE: [148, 149, 150],
  BUSH: [172, 173],
  FENCE: [168, 169, 170, 171],
  HOUSE_WALL: [240, 241, 264, 265],
  HOUSE_ROOF: [336, 337, 360, 361],
  DOOR: [312, 313, 336, 337],
  CHEST: [384], BARREL: [385], SIGN: [386],
  FLOWER: [96, 97, 120, 121],
  ROCK: [98, 99, 122, 123],
  SAND: [54, 55, 78, 79],
  BRIDGE: [456, 457, 480, 481],
};

export class GameScene extends Phaser.Scene {
  private sprites: Map<string, CharacterSprite> = new Map();
  private ts = CONFIG.TILE.size;
  private iconTexts: Phaser.GameObjects.Text[] = [];
  private tileGids: Record<string, number[]> = TG;

  constructor() { super({ key: "GameScene" }); }

  preload(): void {
    // 加载 Tuxemon tileset / Load Tuxemon tileset
    this.load.image("rpg_tileset", "/assets/rpg_tileset.png");
  }

  create(): void {
    const st = gameStore.getState();
    this.genSprites(st.characters);
    gameStore.subscribe(s => this.onUpdate(s));
    if (st.scenes.length > 0) this.buildMap(st.scenes[0], st.scene_objects);
    this.events.on("character-clicked", (c: any) => document.dispatchEvent(new CustomEvent("character-selected", { detail: c })));
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
      c.fillStyle = body; c.fillRect(cx - 6, 11, 12, 10);
      c.fillStyle = skin; c.beginPath(); c.arc(cx, 10, 6, 0, Math.PI * 2); c.fill();
      c.fillStyle = hair; c.beginPath(); c.arc(cx, 8, 6, Math.PI, Math.PI * 2); c.fill();
      c.fillStyle = "#000"; c.fillRect(cx - 3, 9, 2, 2); c.fillRect(cx + 1, 9, 2, 2);
      c.fillStyle = "#2c3e50"; c.fillRect(cx - 5, 21, 4, 7); c.fillRect(cx + 1, 21, 4, 7);
      if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 8, 12, 3, 4); c.fillRect(cx + 5, 12, 3, 4); }
      cv.refresh();
    }
  }

  /* ═════════════════════ Tuxemon 地图 / Tuxemon map ═════════════════════ */
  private buildMap(scene: SceneData, objs: Array<{ id: string; name: string; object_type: string; scene_id: string; position_x: number; position_y: number }>): void {
    const s = this.ts, C = 30, R = 20;
    const g = this.tileGids;
    const pick = (arr: number[]) => arr[Math.floor(Math.random() * arr.length)];
    const map: number[][] = [];
    for (let r = 0; r < R; r++) { map[r] = []; for (let c = 0; c < C; c++) map[r][c] = pick(g.GRASS); }

    // 水域 / Water
    for (let r = 6; r < 9; r++) for (let c = 20; c < 26; c++) map[r][c] = pick(g.WATER);
    for (let r = 14; r < 16; r++) for (let c = 3; c < 7; c++) map[r][c] = pick(g.WATER);
    // 沙地岸边 / Sand shore
    for (let c = 19; c < 27; c++) map[5]![c] = pick(g.SAND);
    for (let c = 2; c < 8; c++) map[13]![c] = pick(g.SAND);

    // 土路 / Dirt paths
    for (let i = 0; i < C; i++) { map[4]![i] = pick(g.DIRT); map[10]![i] = pick(g.PATH); }
    for (let i = 0; i < R; i++) { map[i]![8] = pick(g.PATH); map[i]![18] = pick(g.DIRT); }

    // 树木 / Trees
    for (let r = 2; r < 4; r++) for (let c = 2; c < 5; c++) map[r][c] = pick(g.TREE);
    for (let r = 12; r < 14; r++) for (let c = 22; c < 25; c++) map[r][c] = pick(g.TREE);
    for (let r = 15; r < 17; r++) for (let c = 1; c < 3; c++) map[r][c] = pick(g.TREE);

    // 灌木 + 石头 + 花 / Bushes + rocks + flowers
    for (let i = 0; i < 5; i++) map[2]![10 + i] = pick(g.BUSH);
    for (let i = 0; i < 3; i++) map[6]![15 + i] = pick(g.ROCK);
    for (let i = 0; i < 4; i++) map[8]![22 + i] = pick(g.FLOWER);
    for (let i = 0; i < 3; i++) map[15]![10 + i * 2] = pick(g.BUSH);

    // 房子 / House (右下角)
    for (let r = 17; r < R; r++) for (let c = 22; c < 28; c++) {
      if (r === 17) map[r][c] = pick(g.HOUSE_ROOF);
      else map[r][c] = pick(g.HOUSE_WALL);
    }
    map[18]![24] = pick(g.DOOR);  // 门 / Door

    // 栅栏 / Fence
    for (let c = 19; c < 22; c++) map[16]![c] = pick(g.FENCE);

    // 出口 → 沙地 / Exits → sand
    for (const ex of scene.exits || []) {
      const ec = Math.min(ex.position.x, C - 1), er = Math.min(ex.position.y, R - 1);
      map[er]![ec] = pick(g.SAND); map[Math.min(er + 1, R - 1)]![ec] = pick(g.SAND);
    }

    // 地标装饰 / Landmark decor
    for (const lm of scene.landmarks || []) {
      const lc = Math.min(Math.max(lm.position.x, 1), C - 2), lr = Math.min(Math.max(lm.position.y, 1), R - 2);
      if (lm.id.includes("tavern")) { map[lr]![lc] = pick(g.SIGN); map[lr]![lc + 1] = pick(g.BARREL); }
      else if (lm.id.includes("blacksmith")) { map[lr]![lc] = pick(g.SIGN); }
      else if (lm.id.includes("market")) { map[lr]![lc] = pick(g.SIGN); map[lr]![lc + 1] = pick(g.CHEST); }
    }

    // Tuxemon tileset: 816x1020, 24列, margin=1, spacing=2, 32x32 tiles
    const tilemap = this.make.tilemap({
      data: map, tileWidth: s, tileHeight: s,
      width: C, height: R,
    });
    // 第1个瓦片在图片中偏移(1,1)，瓦片间隔=34px(32+2)
    const tileset = tilemap.addTilesetImage(
      "tuxemon-sample-32px-extruded",  // tileset 名称（和 Tiled 里一致）
      "rpg_tileset",                    // Phaser 缓存 key
      s, s,                              // 瓦片尺寸
      1, 2,                              // margin=1px, spacing=2px
    );
    if (!tileset) return;
    const layer = tilemap.createLayer(0, tileset!, 0, 0);

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
      const t2 = this.add.text((obj.position_x % C) * s + s / 2, (obj.position_y % R) * s + s / 2 - 4,
        icons[obj.object_type] || "❓", { fontSize: `${s * 0.4}px` }).setOrigin(0.5).setDepth(15);
      this.iconTexts.push(t2);
    }
  }

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
