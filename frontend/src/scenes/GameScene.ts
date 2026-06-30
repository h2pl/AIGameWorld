/** 主游戏场景 / Main Game Scene — 遵循 phaser-rpg 标准模式 + 全链路日志 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import { KEY, DEPTH, TILEMAP } from "../constants";

const L = "[Scene]"; // 日志前缀 / Log prefix

const RACE_SKIN: Record<string, string> = { human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574", halfling: "#f5c6a0", orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c" };
const RACE_HAIR: Record<string, string> = { human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513", halfling: "#6b3a1f", orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00" };
const ROLE_COLOR: Record<string, string> = { fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f", ranger: "#27ae60", paladin: "#f1c40f", blacksmith: "#a0522d", guard: "#2980b9", merchant: "#16a085", innkeeper: "#d35400", boss: "#e74c3c", enemy: "#c0392b", villager: "#95a5a6" };

function makeCharTexture(
  scene: Phaser.Scene,
  ch: { id: string; race: string | null; role: string; is_pc: boolean; functions?: string[] },
  size: number,
): void {
  if (scene.textures.exists(ch.id)) return;
  const skin = RACE_SKIN[ch.race || ""] || "#f5cba7";
  const hair = RACE_HAIR[ch.race || ""] || "#4a2c0a";
  const body = ROLE_COLOR[ch.role] || (ch.functions?.[0] ? ROLE_COLOR[ch.functions[0]] || "#7f8c8d" : "#7f8c8d");
  const cv = scene.textures.createCanvas(ch.id, size, size);
  if (!cv) return;
  const c = cv.context; c.imageSmoothingEnabled = false;
  const cx = size / 2;
  c.fillStyle = body; c.fillRect(cx - 6, 11, 12, 10);
  c.fillStyle = skin; c.beginPath(); c.arc(cx, 9, 6, 0, Math.PI * 2); c.fill();
  c.fillStyle = hair; c.beginPath(); c.arc(cx, 7, 6, Math.PI, Math.PI * 2); c.fill();
  c.fillStyle = "#fff"; c.fillRect(cx - 2, 8, 1, 2); c.fillRect(cx + 1, 8, 1, 2);
  c.fillStyle = "#000"; c.fillRect(cx - 2, 9, 1, 1); c.fillRect(cx + 1, 9, 1, 1);
  c.fillStyle = "#2c3e50"; c.fillRect(cx - 4, 20, 4, 6); c.fillRect(cx + 1, 20, 4, 6);
  if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 7, 12, 3, 3); c.fillRect(cx + 4, 12, 3, 3); }
  cv.refresh();
  console.log(`${L} texture created: ${ch.id} pc=${ch.is_pc} role=${ch.role} race=${ch.race}`);
}

export class GameScene extends Phaser.Scene {
  private sprites: Map<string, CharacterSprite> = new Map();
  private ts = 32;
  private iconTexts: Phaser.GameObjects.Text[] = [];
  private narrativeText: Phaser.GameObjects.Text | null = null;
  private tilemap!: Phaser.Tilemaps.Tilemap;
  private worldLayer!: Phaser.Tilemaps.TilemapLayer;
  private unsubscribe: (() => void) | null = null;

  constructor() { super({ key: "Game" }); }

  create(): void {
    this.ts = TILEMAP.TILE_SIZE;
    const st = gameStore.getState();
    console.log(`${L} === create() START === chars=${st.characters.length} scenes=${st.scenes.length}`,);

    // ── 1. 纹理 / Textures ──
    this.ensureFallbackTextures();
    for (const ch of st.characters) makeCharTexture(this, ch, this.ts);
    console.log(`${L} textures ready`);

    // ── 2. 地图 / Tilemap ──
    this.tilemap = this.make.tilemap({ key: KEY.TILEMAP.TUXEMON });
    const tileset = this.tilemap.addTilesetImage(TILEMAP.TILESET_NAME, KEY.IMAGE.TUXEMON);
    if (!tileset) { console.error(`${L} ERROR: Tileset not found!`); return; }
    console.log(`${L} tileset loaded: ${TILEMAP.TILESET_NAME}`);

    this.tilemap.createLayer(TILEMAP.LAYERS.BELOW, tileset, 0, 0);
    this.worldLayer = this.tilemap.createLayer(TILEMAP.LAYERS.WORLD, tileset, 0, 0)!;
    this.worldLayer.setCollisionByProperty({ collides: true });
    const aboveLayer = this.tilemap.createLayer(TILEMAP.LAYERS.ABOVE, tileset, 0, 0)!;
    aboveLayer.setDepth(DEPTH.ABOVE_PLAYER);
    console.log(`${L} 3 layers created. Above depth=${DEPTH.ABOVE_PLAYER}`);

    // 物理世界边界 / Physics world bounds
    const mapW = this.tilemap.widthInPixels;
    const mapH = this.tilemap.heightInPixels;
    this.physics.world.bounds.width = mapW;
    this.physics.world.bounds.height = mapH;
    console.log(`${L} map size: ${mapW}x${mapH}px (${mapW / this.ts}x${mapH / this.ts} tiles)`);

    // ── 3. 摄像机 / Camera ──
    this.cameras.main.setBounds(0, 0, mapW, mapH);
    // 计算包围所有角色的最小区域，居中显示
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const ch of st.characters) {
      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      minX = Math.min(minX, p.x); minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x); maxY = Math.max(maxY, p.y);
    }
    const cx = ((minX + maxX) / 2 + 0.5) * this.ts;
    const cy = ((minY + maxY) / 2 + 0.5) * this.ts;
    this.cameras.main.centerOn(cx, cy);
    console.log(`${L} camera centerOn (${cx.toFixed(0)},${cy.toFixed(0)}) — char range tile(${minX},${minY})→(${maxX},${maxY}) cam scroll=(${this.cameras.main.scrollX.toFixed(0)},${this.cameras.main.scrollY.toFixed(0)})`,);

    // ── 4. 放置角色 / Place characters ──
    this.placeCharacters();

    // ── 5. 场景对象 / Scene objects ──
    this.placeSceneObjects(st.scene_objects);

    // ── 6. 事件 / Events ──
    this.events.on("character-clicked", (c: unknown) => {
      console.log(`${L} character-clicked:`, (c as { id: string }).id);
      document.dispatchEvent(new CustomEvent("character-selected", { detail: c }));
    });

    // ── 7. 订阅 store / Subscribe ──
    this.unsubscribe = gameStore.subscribe(() => this.onStoreUpdate());
    console.log(`${L} store subscribed`);

    // ── 8. HUD ──
    this.narrativeText = this.add.text(10, CONFIG.CANVAS.height - 48,
      "连接后端后点 [▶] 开始 / Connect backend then press [▶]",
      { fontFamily: "Segoe UI, sans-serif", fontSize: "13px", color: "#ffd700",
        backgroundColor: "rgba(0,0,0,0.7)", padding: { x: 10, y: 6 },
        wordWrap: { width: CONFIG.CANVAS.width - 20 },
      },
    ).setScrollFactor(0).setDepth(DEPTH.HUD);

    const scene = st.scenes[0];
    const labels: Record<string, string> = { village: "村庄", indoor: "室内", outdoor: "野外", underground: "地下" };
    this.add.text(8, 4, `${scene?.name || "Tuxemon Town"} (${labels[scene?.type || "outdoor"]})`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setScrollFactor(0).setDepth(DEPTH.HUD);

    console.log(`${L} === create() DONE === sprites=${this.sprites.size}`);
  }

  private ensureFallbackTextures(): void {
    const fallback = [
      { id: "pc_fighter", race: "human", role: "fighter", is_pc: true },
      { id: "actor_default", race: "human", role: "villager", is_pc: false },
    ];
    for (const fb of fallback) makeCharTexture(this, fb, this.ts);
  }

  /** 按数据位置放置所有角色 / Place all characters at their data positions */
  private placeCharacters(): void {
    const st = gameStore.getState();
    console.log(`${L} placeCharacters: ${st.characters.length} chars`);
    for (const ch of st.characters) {
      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      let { x: tx, y: ty } = p;
      // 碰撞检查 / Collision check
      if (this.worldLayer) {
        const tile = this.worldLayer.getTileAt(tx, ty);
        if (tile?.properties?.collides) {
          const offsets = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]];
          for (const [dx, dy] of offsets) {
            const nt = this.worldLayer.getTileAt(tx + dx, ty + dy);
            if (!nt || !nt.properties?.collides) { tx += dx; ty += dy; break; }
          }
        }
      }
      gameStore.getState().character_positions[ch.id] = { x: tx, y: ty };
      console.log(`${L}   ${ch.id} data(${ch.position_x},${ch.position_y}) placed(${tx},${ty}) pixel(${tx * this.ts + this.ts / 2},${ty * this.ts + this.ts / 2}) pc=${ch.is_pc}`);
    }
    this.renderAllSprites();
  }

  /** 渲染所有角色精灵 / Render all character sprites */
  private renderAllSprites(): void {
    const st = gameStore.getState();
    let destroyed = 0, created = 0, moved = 0;
    // 清理 / Cleanup
    for (const [id, sp] of this.sprites) {
      if (!st.characters.find(c => c.id === id)) {
        sp.destroy(); this.sprites.delete(id);
        destroyed++;
      }
    }
    // 创建/更新 / Create/update
    for (const ch of st.characters) {
      if (!this.textures.exists(ch.id)) makeCharTexture(this, ch, this.ts);
      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      const wx = p.x * this.ts + this.ts / 2;
      const wy = p.y * this.ts + this.ts / 2;
      const existing = this.sprites.get(ch.id);
      if (existing) {
        existing.moveToWorld(wx, wy, 300);
        if (ch.combat) existing.updateHp(ch.combat.hp, ch.combat.max_hp);
        moved++;
      } else {
        const sp = new CharacterSprite(this, ch, wx, wy, this.ts);
        sp.setDepth(DEPTH.CHARACTER);
        this.sprites.set(ch.id, sp);
        created++;
      }
    }
    console.log(`${L} renderAllSprites: created=${created} moved=${moved} destroyed=${destroyed} total=${this.sprites.size}`);
  }

  private placeSceneObjects(objs: Array<{ id: string; name: string; object_type: string; scene_id: string; position_x: number; position_y: number }>): void {
    this.iconTexts.forEach(t => t.destroy()); this.iconTexts = [];
    const icons: Record<string, string> = { container: "📦", door: "🚪", trap: "⚠", mechanism: "⚙", decoration: "🏺", item_drop: "✦" };
    for (const obj of objs) {
      const t = this.add.text(
        obj.position_x * this.ts + this.ts / 2,
        obj.position_y * this.ts + this.ts / 2 - 4,
        icons[obj.object_type] || "❓",
        { fontSize: "14px" },
      ).setOrigin(0.5).setDepth(DEPTH.CHARACTER + 5);
      this.iconTexts.push(t);
    }
  }

  /** WS/Store 驱动的增量更新 / WS/Store driven incremental update */
  private onStoreUpdate(): void {
    const st = gameStore.getState();
    console.log(`${L} onStoreUpdate: tick=${st.current_tick} chars=${st.characters.length} narrative=${st.narrative ? st.narrative.slice(0, 30) + "..." : "(none)"}`);
    for (const ch of st.characters) {
      if (!this.textures.exists(ch.id)) makeCharTexture(this, ch, this.ts);
    }
    this.renderAllSprites();
    if (st.narrative && this.narrativeText) this.narrativeText.setText(st.narrative);
  }

  setNarrative(text: string): void {
    console.log(`${L} setNarrative: ${text.slice(0, 40)}...`);
    if (this.narrativeText) this.narrativeText.setText(text || this.narrativeText.text);
  }

  shutdown(): void {
    if (this.unsubscribe) this.unsubscribe();
  }
}
