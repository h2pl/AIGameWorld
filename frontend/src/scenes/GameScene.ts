/** 主游戏场景 / Main Game Scene — kb/17 初始化顺序 */
import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterManager } from "../managers/CharacterManager";
import { CONFIG } from "../config";
import { KEY, DEPTH, TILEMAP, SCENE_MAP } from "../constants";
import { gridToWorld } from "../utils/tile";

/** 种族肤色 / Race skin colors */
const RACE_SKIN: Record<string, string> = { human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574", halfling: "#f5c6a0", orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c" };
/** 种族发色 / Race hair colors */
const RACE_HAIR: Record<string, string> = { human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513", halfling: "#6b3a1f", orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00" };
/** 职业色 / Role colors */
const ROLE_COLOR: Record<string, string> = { fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f", ranger: "#27ae60", paladin: "#f1c40f", blacksmith: "#a0522d", guard: "#2980b9", merchant: "#16a085", innkeeper: "#d35400", boss: "#e74c3c", enemy: "#c0392b", villager: "#95a5a6" };

/** 生成单个角色 Canvas 纹理 / Generate character Canvas texture */
function makeCharTexture(scene: Phaser.Scene, ch: { id: string; race: string | null; role: string; is_pc: boolean; functions?: string[] }, size: number): void {
  if (scene.textures.exists(ch.id)) return;
  const skin = RACE_SKIN[ch.race || ""] || "#f5cba7";
  const hair = RACE_HAIR[ch.race || ""] || "#4a2c0a";
  const body = ROLE_COLOR[ch.role] || (ch.functions?.[0] ? ROLE_COLOR[ch.functions[0]] || "#7f8c8d" : "#7f8c8d");
  const cv = scene.textures.createCanvas(ch.id, size, size);
  if (!cv) return;
  const c = cv.context; c.imageSmoothingEnabled = false;
  const cx = size / 2;
  c.fillStyle = body; c.fillRect(cx - 6, 11, 12, 10);           // body
  c.fillStyle = skin; c.beginPath(); c.arc(cx, 9, 6, 0, Math.PI * 2); c.fill(); // head
  c.fillStyle = hair; c.beginPath(); c.arc(cx, 7, 6, Math.PI, Math.PI * 2); c.fill(); // hair
  c.fillStyle = "#fff"; c.fillRect(cx - 2, 8, 1, 2); c.fillRect(cx + 1, 8, 1, 2); // eyes
  c.fillStyle = "#000"; c.fillRect(cx - 2, 9, 1, 1); c.fillRect(cx + 1, 9, 1, 1); // pupils
  c.fillStyle = "#2c3e50"; c.fillRect(cx - 4, 20, 4, 6); c.fillRect(cx + 1, 20, 4, 6); // legs
  if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 7, 12, 3, 3); c.fillRect(cx + 4, 12, 3, 3); }
  cv.refresh();
}

/** 生成场景物品纹理 / Generate scene object texture */
function makeObjectTexture(scene: Phaser.Scene, obj: { id: string; object_type: string }, key: string, size: number): void {
  const colors: Record<string, string> = { container: "#d4a017", door: "#8b6914", landmark: "#ccc" };
  const fill = colors[obj.object_type] || "#888";
  const cv = scene.textures.createCanvas(key, size, size);
  if (!cv) return;
  const c = cv.context; c.imageSmoothingEnabled = false;
  c.fillStyle = fill;
  if (obj.object_type === "container") {
    c.fillRect(4, 10, 24, 16); c.fillStyle = "#fff"; c.fillRect(12, 16, 8, 2);
  } else if (obj.object_type === "door") {
    c.fillRect(8, 4, 16, 24);
  } else {
    c.beginPath(); c.arc(size / 2, size / 2, 8, 0, Math.PI * 2); c.fill();
  }
  cv.refresh();
}

export class GameScene extends Phaser.Scene {
  private ts!: number;
  private tilemap!: Phaser.Tilemaps.Tilemap;
  private charManager!: CharacterManager;
  private sceneNameText!: Phaser.GameObjects.Text;
  private narrativeText!: Phaser.GameObjects.Text;
  private unsubscribe: (() => void) | null = null;
  private mapKey!: string;

  constructor() { super({ key: "Game" }); }

  // ══ kb/17 初始化顺序 / Init order ══

  create(data?: { mapKey?: string }): void {
    this.mapKey = data?.mapKey || KEY.TILEMAP.TUXEMON;
    this.initVariables();
    this.initCamera();
    this.initPhysics();         // ⏭️ TODO
    this.createBackground();
    this.createGroups();        // ⏭️ TODO
    this.createLevel();
    this.createTerrain();
    this.createPlayer();
    this.createEnemies();       // ⏭️ TODO
    this.initAnimations();      // ⏭️ TODO
    this.initInput();
    this.setupCollisions();     // ⏭️ TODO
    this.createUI();
    this.cameras.main.fadeIn(400, 0, 0, 0);
  }

  /** 1. initVariables / Reset state + 生成纹理 */
  private initVariables(): void {
    this.ts = TILEMAP.TILE_SIZE;
    const st = gameStore.getState();
    // 为所有角色生成 Canvas 纹理 / Generate Canvas textures for all characters
    for (const ch of st.characters) makeCharTexture(this, ch, this.ts);
    // fallback 纹理 / Fallback textures
    for (const fb of [{ id: "fighter_fb", race: "human", role: "fighter", is_pc: true }, { id: "actor_fb", race: "human", role: "villager", is_pc: false }]) {
      makeCharTexture(this, fb, this.ts);
    }
    console.log("[Scene] initVariables ts=%d chars=%d textures=ready", this.ts, st.characters.length);
  }

  /** 2. initCamera / Camera config */
  private initCamera(): void {
    // setBounds 在 createLevel 中执行（需 tilemap 尺寸）
  }

  /** 3. initPhysics / Physics world — TODO: PMove 实时操控时启用 */
  private initPhysics(): void {
    // 当前跳过：kb/18 "Skip Physics When: Grid-based movement"
  }

  /** 4. createBackground / Background visuals */
  private createBackground(): void {
    this.tilemap = this.make.tilemap({ key: this.mapKey });
    const tsImageKey = this.mapKey === KEY.TILEMAP.DESERT ? KEY.IMAGE.DESERT : KEY.IMAGE.TUXEMON;
    const tsName = this.mapKey === KEY.TILEMAP.DESERT ? "Desert" : TILEMAP.TILESET_NAME;
    const tileset = this.tilemap.addTilesetImage(tsName, tsImageKey);
    if (!tileset) { console.error("[Scene] tileset FAIL for", this.mapKey); return; }
    this.tilemap.createLayer(TILEMAP.LAYERS.BELOW, tileset, 0, 0);
    console.log("[Scene] createBackground map=", this.mapKey);
  }

  /** 6a. createTerrain / 场景物品渲染 */
  private createTerrain(): void {
    for (const obj of gameStore.getState().scene_objects) {
      const key = `obj_${obj.id}`;
      if (!this.textures.exists(key)) makeObjectTexture(this, obj, key, this.ts);
      const { wx, wy } = gridToWorld(obj.position_x, obj.position_y, this.ts);
      this.add.sprite(wx, wy, key).setOrigin(0.5, 1).setDepth(DEPTH.CHARACTER - 1)
        .setInteractive({ useHandCursor: true })
        .on("pointerdown", () => {
          console.log("[Scene] interacted with:", obj.name);
          document.dispatchEvent(new CustomEvent("object-interacted", { detail: obj }));
        });
    }
    console.log("[Scene] createTerrain objects=%d", gameStore.getState().scene_objects.length);
  }

  /** 5. createGroups / Physics groups — TODO: 对象池化频繁创建的对象 */
  private createGroups(): void {
    // 当前跳过：无 physics groups
  }

  /** 6. createLevel / Static objects: World + Above layers + collision props */
  private createLevel(): void {
    const tsName = this.mapKey === KEY.TILEMAP.DESERT ? "Desert" : TILEMAP.TILESET_NAME;
    const ts = this.tilemap.getTileset(tsName);
    if (!ts) return;
    const worldLayer = this.tilemap.createLayer(TILEMAP.LAYERS.WORLD, ts, 0, 0)!;
    worldLayer.setCollisionByProperty({ collides: true });
    const aboveLayer = this.tilemap.createLayer(TILEMAP.LAYERS.ABOVE, ts, 0, 0)!;
    aboveLayer.setDepth(DEPTH.ABOVE_PLAYER);

    const mapW = this.tilemap.widthInPixels;
    const mapH = this.tilemap.heightInPixels;
    this.cameras.main.setBounds(0, 0, mapW, mapH);
    console.log("[Scene] createLevel map=%dx%d px", mapW, mapH);
  }

  /** 7. createPlayer / Dynamic objects: 所有角色 */
  private createPlayer(): void {
    this.charManager = new CharacterManager(this, this.ts);
    const st = gameStore.getState();
    this.charManager.createAll(st.characters, st.character_positions);
    const { sx, sy } = this.charManager.calcCameraScroll(CONFIG.CANVAS.width, CONFIG.CANVAS.height);
    this.cameras.main.scrollX = sx;
    this.cameras.main.scrollY = sy;
    console.log("[Scene] createPlayer total=%d camScroll=(%d,%d)", st.characters.length, sx.toFixed(0), sy.toFixed(0));
  }

  /** 8. createEnemies / Spawned objects — TODO: 敌对 NPC 自动生成 */
  private createEnemies(): void {
    // 当前跳过：无 enemy 系统
  }

  /** 9. initAnimations / Animation setup — TODO: 替换 Canvas 为 spritesheet */
  private initAnimations(): void {
    // 当前跳过：Canvas 纹理无帧动画
  }

  /** 10. initInput / Input handlers */
  private initInput(): void {
    this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      const wp = this.cameras.main.getWorldPoint(pointer.x, pointer.y);
      const st = gameStore.getState();
      for (const ch of st.characters) {
        const p = st.character_positions[ch.id] || { x: ch.position_x, y: ch.position_y };
        const cx = p.x * this.ts + this.ts / 2;
        const cy = p.y * this.ts + this.ts / 2;
        if (Math.abs(wp.x - cx) < 20 && Math.abs(wp.y - cy) < 20) {
          console.log("[Scene] clicked character:", ch.name);
          document.dispatchEvent(new CustomEvent("character-selected", { detail: ch }));
          break;
        }
      }
    });
  }

  /** 11. setupCollisions / Collision rules — TODO: 战斗碰撞 / 交互碰撞 */
  private setupCollisions(): void {
    // 当前跳过：无 physics 碰撞体
  }

  /** 12. createUI / HUD overlay + store subscribe + 场景切换 */
  private createUI(): void {
    const st = gameStore.getState();
    const scene = st.scenes[0];
    this.sceneNameText = this.add.text(8, 4, `${scene?.name || ""}`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setScrollFactor(0).setDepth(DEPTH.HUD);

    this.narrativeText = this.add.text(10, CONFIG.CANVAS.height - 40,
      "",
      { fontFamily: "Segoe UI, sans-serif", fontSize: "13px", color: "#ffd700",
        backgroundColor: "rgba(0,0,0,0.7)", padding: { x: 10, y: 6 } },
    ).setScrollFactor(0).setDepth(DEPTH.HUD);

    // 订阅 store / Subscribe to store
    let lastSceneId = st.characters[0]?.scene_id;
    this.unsubscribe = gameStore.subscribe(() => {
      const s = gameStore.getState();
      this.charManager.sync(s.characters, s.character_positions);
      if (s.narrative && this.narrativeText) this.narrativeText.setText(s.narrative);
      // 场景切换检测 / Scene change detection
      const curSceneId = s.characters[0]?.scene_id;
      if (curSceneId && curSceneId !== lastSceneId) {
        lastSceneId = curSceneId;
        this.onSceneChanged(curSceneId);
      }
    });

    // 场景切换内部逻辑 / Scene change handler (commented: used by CharacterManager for future explicit triggers)

    console.log("[Scene] createUI done, store subscribed");
  }

  /** 场景切换 / Switch scene — 淡出→重启→淡入 / Fade out → restart → fade in */
  private onSceneChanged(sceneId: string): void {
    const cfg = SCENE_MAP[sceneId];
    if (!cfg || cfg.map === this.mapKey) return;
    console.log("[Scene] scene-changed →", sceneId, "restarting with", cfg.map);
    this.cameras.main.fadeOut(400, 0, 0, 0);
    this.cameras.main.once("camerafadeoutcomplete", () => {
      this.scene.start("Game", { mapKey: cfg.map });
    });
  }

  // ══ Lifecycle ══

  setNarrative(text: string): void {
    if (this.narrativeText) this.narrativeText.setText(text);
  }

  shutdown(): void {
    if (this.unsubscribe) this.unsubscribe();
    this.charManager?.destroy();
  }
}
