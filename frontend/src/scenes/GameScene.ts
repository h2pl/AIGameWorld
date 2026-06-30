/** 主游戏场景 / Main Game Scene — 遵循 phaser-rpg 标准模式 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import { KEY, DEPTH, TILEMAP } from "../constants";

const RACE_SKIN: Record<string, string> = { human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574", halfling: "#f5c6a0", orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c" };
const RACE_HAIR: Record<string, string> = { human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513", halfling: "#6b3a1f", orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00" };
const ROLE_COLOR: Record<string, string> = { fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f", ranger: "#27ae60", paladin: "#f1c40f", blacksmith: "#a0522d", guard: "#2980b9", merchant: "#16a085", innkeeper: "#d35400", boss: "#e74c3c", enemy: "#c0392b", villager: "#95a5a6" };

/** 生成单个角色纹理 / Generate single character texture */
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
  c.fillStyle = body; c.fillRect(cx - 6, 11, 12, 10);          // 身体/body
  c.fillStyle = skin; c.beginPath(); c.arc(cx, 9, 6, 0, Math.PI * 2); c.fill(); // 头/head
  c.fillStyle = hair; c.beginPath(); c.arc(cx, 7, 6, Math.PI, Math.PI * 2); c.fill(); // 头发/hair
  c.fillStyle = "#fff"; c.fillRect(cx - 2, 8, 1, 2); c.fillRect(cx + 1, 8, 1, 2); // 眼白/eye whites
  c.fillStyle = "#000"; c.fillRect(cx - 2, 9, 1, 1); c.fillRect(cx + 1, 9, 1, 1); // 瞳孔/pupils
  c.fillStyle = "#2c3e50"; c.fillRect(cx - 4, 20, 4, 6); c.fillRect(cx + 1, 20, 4, 6); // 腿/legs
  if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 7, 12, 3, 3); c.fillRect(cx + 4, 12, 3, 3); } // PC 标识
  cv.refresh();
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

    // ── 1. 确保所有角色都有纹理 / Ensure all characters have textures ──
    // 包括 fallback 纹理 / Include fallback textures
    this.ensureFallbackTextures();
    for (const ch of st.characters) makeCharTexture(this, ch, this.ts);

    // ── 2. 建造地图 (与 phaser-rpg 一致) / Build map (same as phaser-rpg) ──
    this.tilemap = this.make.tilemap({ key: KEY.TILEMAP.TUXEMON });
    const tileset = this.tilemap.addTilesetImage(TILEMAP.TILESET_NAME, KEY.IMAGE.TUXEMON);
    if (!tileset) { console.error("Tileset not found!"); return; }

    // 3 层: Below → World(碰撞) → Above(树冠) / 3 layers
    this.tilemap.createLayer(TILEMAP.LAYERS.BELOW, tileset, 0, 0);
    this.worldLayer = this.tilemap.createLayer(TILEMAP.LAYERS.WORLD, tileset, 0, 0)!;
    this.worldLayer.setCollisionByProperty({ collides: true });
    const aboveLayer = this.tilemap.createLayer(TILEMAP.LAYERS.ABOVE, tileset, 0, 0)!;
    aboveLayer.setDepth(DEPTH.ABOVE_PLAYER);

    // 物理世界边界 / Physics world bounds
    this.physics.world.bounds.width = this.tilemap.widthInPixels;
    this.physics.world.bounds.height = this.tilemap.heightInPixels;

    // ── 3. 摄像机 / Camera ──
    const mapW = this.tilemap.widthInPixels;
    const mapH = this.tilemap.heightInPixels;
    this.cameras.main.setBounds(0, 0, mapW, mapH);

    // 找到第一个 PC 作为摄像机跟随目标 / Find first PC as camera follow target
    const firstPC = st.characters.find(c => c.is_pc);
    if (firstPC) {
      const pcx = (firstPC.position_x + 0.5) * this.ts;
      const pcy = (firstPC.position_y + 0.5) * this.ts;
      this.cameras.main.centerOn(pcx, pcy);
    } else {
      // 回退: 居中地图 / Fallback: center on map
      this.cameras.main.centerOn(mapW / 2, mapH / 2);
    }

    // ── 4. 放置角色 / Place characters ──
    this.placeCharacters();

    // ── 5. 场景对象图标 / Scene object icons ──
    this.placeSceneObjects(st.scene_objects);

    // ── 6. 事件监听 / Event listeners ──
    this.events.on("character-clicked", (c: unknown) =>
      document.dispatchEvent(new CustomEvent("character-selected", { detail: c })));

    // 监听 store 变化做增量更新 / Listen to store for incremental updates
    this.unsubscribe = gameStore.subscribe(() => this.onStoreUpdate());

    // ── 7. 叙事区 / Narrative overlay ──
    this.narrativeText = this.add.text(10, CONFIG.CANVAS.height - 48,
      "连接后端后点 [▶] 开始 / Connect backend then press [▶]",
      {
        fontFamily: "Segoe UI, sans-serif", fontSize: "13px", color: "#ffd700",
        backgroundColor: "rgba(0,0,0,0.7)", padding: { x: 10, y: 6 },
        wordWrap: { width: CONFIG.CANVAS.width - 20 },
      },
    ).setScrollFactor(0).setDepth(DEPTH.HUD);

    // ── 8. 场景标题 HUD / Scene title HUD ──
    const scene = st.scenes[0];
    const labels: Record<string, string> = { village: "村庄", indoor: "室内", outdoor: "野外", underground: "地下" };
    this.add.text(8, 4, `${scene?.name || "Tuxemon Town"} (${labels[scene?.type || "outdoor"]})`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setScrollFactor(0).setDepth(DEPTH.HUD);
  }

  /** 确保 fallback 纹理存在 / Ensure fallback textures exist */
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
    for (const ch of st.characters) {
      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      // 检查碰撞：如果位置在碰撞 tile 上，尝试偏移 / Check collision: if on colliding tile, try offset
      let { x: tx, y: ty } = p;
      if (this.worldLayer) {
        const tile = this.worldLayer.getTileAt(tx, ty);
        if (tile?.properties?.collides) {
          // 尝试邻近位置 / Try adjacent positions
          const offsets = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]];
          for (const [dx, dy] of offsets) {
            const nt = this.worldLayer.getTileAt(tx + dx, ty + dy);
            if (!nt || !nt.properties?.collides) { tx += dx; ty += dy; break; }
          }
        }
      }
      gameStore.getState().character_positions[ch.id] = { x: tx, y: ty };
    }
    this.renderAllSprites();
  }

  /** 渲染所有角色精灵 / Render all character sprites */
  private renderAllSprites(): void {
    const st = gameStore.getState();
    // 销毁已不存在的角色精灵 / Destroy sprites for characters no longer in store
    for (const [id, sp] of this.sprites) {
      if (!st.characters.find(c => c.id === id)) { sp.destroy(); this.sprites.delete(id); }
    }
    // 创建/更新每个角色的精灵 / Create/update each character's sprite
    for (const ch of st.characters) {
      // 确保纹理 / Ensure texture
      if (!this.textures.exists(ch.id)) makeCharTexture(this, ch, this.ts);

      const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
      const wx = p.x * this.ts + this.ts / 2;
      const wy = p.y * this.ts + this.ts / 2;
      const existing = this.sprites.get(ch.id);
      if (existing) {
        existing.moveToWorld(wx, wy, 300);
        if (ch.combat) existing.updateHp(ch.combat.hp, ch.combat.max_hp);
      } else {
        const sp = new CharacterSprite(this, ch, wx, wy, this.ts);
        sp.setDepth(DEPTH.CHARACTER);
        this.sprites.set(ch.id, sp);
      }
    }
  }

  /** 放置场景对象图标 / Place scene object icons */
  private placeSceneObjects(objs: Array<{ id: string; name: string; object_type: string; scene_id: string; position_x: number; position_y: number }>): void {
    this.iconTexts.forEach(t => t.destroy()); this.iconTexts = [];
    const icons: Record<string, string> = { container: "📦", door: "🚪", trap: "⚠", mechanism: "⚙", decoration: "🏺", item_drop: "✦" };
    const s = this.ts;
    for (const obj of objs) {
      const ox = obj.position_x * s + s / 2;
      const oy = obj.position_y * s + s / 2 - 4;
      const t = this.add.text(ox, oy, icons[obj.object_type] || "❓", { fontSize: "14px" })
        .setOrigin(0.5).setDepth(DEPTH.CHARACTER + 5);
      this.iconTexts.push(t);
    }
  }

  /** Store 更新回调 / Store update callback */
  private onStoreUpdate(): void {
    const st = gameStore.getState();
    // 如果有新角色，生成纹理 / Generate textures for new characters
    for (const ch of st.characters) {
      if (!this.textures.exists(ch.id)) makeCharTexture(this, ch, this.ts);
    }
    this.renderAllSprites();
    if (st.narrative && this.narrativeText) this.narrativeText.setText(st.narrative);
  }

  /** 外部设置叙事文本 / Set narrative text from outside */
  setNarrative(text: string): void {
    if (this.narrativeText) this.narrativeText.setText(text || this.narrativeText.text);
  }

  /** 销毁时清理 / Cleanup on destroy */
  shutdown(): void {
    if (this.unsubscribe) this.unsubscribe();
  }
}
