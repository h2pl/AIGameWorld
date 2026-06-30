/** 主游戏场景 / Main Game Scene — 和 phaser-rpg 一致的标准写法 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import { KEY, DEPTH, TILEMAP } from "../constants";
import type { SceneData } from "../types";

const RACE_SKIN: Record<string, string> = { human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574", halfling: "#f5c6a0", orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c" };
const RACE_HAIR: Record<string, string> = { human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513", halfling: "#6b3a1f", orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00" };
const ROLE_COLOR: Record<string, string> = { fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f", ranger: "#27ae60", paladin: "#f1c40f", blacksmith: "#a0522d", guard: "#2980b9", merchant: "#16a085", innkeeper: "#d35400", boss: "#e74c3c", enemy: "#c0392b", villager: "#95a5a6" };

export class GameScene extends Phaser.Scene {
  private sprites: Map<string, CharacterSprite> = new Map();
  private ts = 32;
  private iconTexts: Phaser.GameObjects.Text[] = [];
  private hudTexts: Phaser.GameObjects.Text[] = [];

  constructor() { super({ key: "Game" }); }

  create(): void {
    this.ts = TILEMAP.TILE_SIZE;
    const st = gameStore.getState();
    this.genSprites(st.characters);
    gameStore.subscribe(s => this.onUpdate(s));
    this.buildMap(st.scenes[0] || {}, st.scene_objects);
    this.events.on("character-clicked", (c: any) => document.dispatchEvent(new CustomEvent("character-selected", { detail: c })));
  }

  /* ═══ 角色精灵 / Character sprites ═══ */
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
      c.fillStyle = skin; c.beginPath(); c.arc(cx, 9, 6, 0, Math.PI * 2); c.fill();
      c.fillStyle = hair; c.beginPath(); c.arc(cx, 7, 6, Math.PI, Math.PI * 2); c.fill();
      c.fillStyle = "#fff"; c.fillRect(cx - 2, 8, 1, 2); c.fillRect(cx + 1, 8, 1, 2); // 白眼球
      c.fillStyle = "#000"; c.fillRect(cx - 2, 9, 1, 1); c.fillRect(cx + 1, 9, 1, 1); // 瞳孔
      c.fillStyle = "#2c3e50"; c.fillRect(cx - 4, 20, 4, 6); c.fillRect(cx + 1, 20, 4, 6);
      if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 7, 12, 3, 3); c.fillRect(cx + 4, 12, 3, 3); }
      cv.refresh();
    }
  }

  /* ═══ 地图：和 phaser-rpg 一样的 3 层 + 碰撞 ═══ */
  private buildMap(scene: SceneData, objs: Array<{ id: string; name: string; object_type: string; scene_id: string; position_x: number; position_y: number }>): void {
    // 用 Tiled JSON 创建地图 / Create tilemap from Tiled JSON
    const map = this.make.tilemap({ key: "tuxemon-map" });
    const tileset = map.addTilesetImage(TILEMAP.TILESET_NAME, KEY.IMAGE.TUXEMON, 32, 32, TILEMAP.MARGIN, TILEMAP.SPACING);
    if (!tileset) return;

    const below = map.createLayer(TILEMAP.LAYERS.BELOW, tileset, 0, 0);
    if (!below) return;

    const world = map.createLayer(TILEMAP.LAYERS.WORLD, tileset, 0, 0)!;
    world.setCollisionByProperty({ collides: true });

    const above = map.createLayer(TILEMAP.LAYERS.ABOVE, tileset, 0, 0)!;
    above.setDepth(DEPTH.ABOVE_PLAYER);

    // 设置摄像机 / Set camera
    const mapW = map.widthInPixels;
    const mapH = map.heightInPixels;
    this.cameras.main.setBounds(0, 0, mapW, mapH);
    // 初始视角：居中城镇区域 / Initial view: center on town
    this.cameras.main.scrollX = Math.max(0, mapW / 2 - CONFIG.CANVAS.width / 2);
    this.cameras.main.scrollY = 50;

    // 角色放在 spawn 附近空地 / Place chars on walkable ground near spawn
    const spawnObj = map.findObject(TILEMAP.LAYERS.OBJECTS, o => o.name === "Spawn Point");
    const spawnTx = Math.floor((spawnObj?.x || 384) / 32);
    const spawnTy = Math.floor((spawnObj?.y || 320) / 32);
    const st2 = gameStore.getState();
    let idx = 0;
    for (const ch of st2.characters) {
      // 每偏移 2 格排开，检查碰撞 / offset 2 tiles each, check collision
      let tx = spawnTx + idx * 2; const ty = spawnTy;
      while (tx < 38) {
        const tile = world.getTileAt(tx, ty);
        if (!tile || !tile.properties?.collides) break;
        tx++;
      }
      st2.character_positions[ch.id] = { x: tx, y: ty };
      idx++;
    }

    this.updateSprites();

    // HUD / 标题
    const labels: Record<string, string> = { village: "村庄", indoor: "室内", outdoor: "野外", underground: "地下" };
    const ttl = this.add.text(8, 4, `${scene.name || "Tuxemon Town"} (${labels[scene.type] || "野外"})`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setScrollFactor(0).setDepth(100);
    this.hudTexts.push(ttl);

    // 场景对象图标
    this.iconTexts.forEach(t => t.destroy()); this.iconTexts = [];
    const icons: Record<string, string> = { container: "📦", door: "🚪", trap: "⚠", mechanism: "⚙", decoration: "🏺", item_drop: "✦" };
    const s = this.ts;
    for (const obj of objs) {
      const ox = obj.position_x * s + s / 2;
      const oy = obj.position_y * s + s / 2 - 4;
      const t2 = this.add.text(ox, oy, icons[obj.object_type] || "❓", { fontSize: "14px" }).setOrigin(0.5).setDepth(25);
      this.iconTexts.push(t2);
    }
  }

  /* ═══ Update ═══ */
  private onUpdate(st: ReturnType<typeof gameStore.getState>): void {
    this.genSprites(st.characters);
    this.updateSprites();
  }

  private updateSprites(): void {
    const st = gameStore.getState();
    for (const [id, sp] of this.sprites) { if (!st.characters.find(c => c.id === id)) { sp.destroy(); this.sprites.delete(id); } }
    for (const ch of st.characters) {
      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      const wx = p.x * this.ts + this.ts / 2;
      const wy = p.y * this.ts + this.ts / 2;
      const ex = this.sprites.get(ch.id);
      if (ex) {
        ex.moveToWorld(wx, wy, 300);
        if (ch.combat) ex.updateHp(ch.combat.hp, ch.combat.max_hp);
      } else {
        const sp = new CharacterSprite(this, ch, wx, wy, this.ts);
        sp.setDepth(10); // 角色在 World 和 Above 之间
        this.sprites.set(ch.id, sp);
      }
    }
  }
}
