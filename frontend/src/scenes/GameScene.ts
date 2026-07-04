/** 主游戏场景 / Main Game Scene — 由 scene_setup 事件驱动初始化 */
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
  private waitingText: Phaser.GameObjects.Text | null = null;
  private unsubscribe: (() => void) | null = null;
  private mapKey!: string;
  private sceneBuilt = false;
  private dialogueQueue: Array<{ speaker_id: string; text: string }> = [];
  private isPlayingDialogue = false;
  private dialogueTimer?: number;
  private dialoguesThisTick = 0;
  private readonly MAX_DIALOGUE_EVENTS_PER_TICK = 1;

  constructor() { super({ key: "Game" }); }

  create(): void {
    this.ts = TILEMAP.TILE_SIZE;
    this.cameras.main.setBackgroundColor("#000000");

    // 预生成角色纹理 / Pre-generate character textures
    const st = gameStore.getState();
    for (const ch of st.characters) makeCharTexture(this, ch, this.ts);
    for (const fb of [{ id: "fighter_fb", race: "human", role: "fighter", is_pc: true }, { id: "actor_fb", race: "human", role: "villager", is_pc: false }]) {
      makeCharTexture(this, fb, this.ts);
    }

    // 等待 DM 创建情境 / Waiting for DM to create situation
    this.waitingText = this.add.text(CONFIG.CANVAS.width / 2, CONFIG.CANVAS.height / 2,
      "等待 DM 创造情境...",
      { fontFamily: "Segoe UI, sans-serif", fontSize: "18px", color: "#ffd700" },
    ).setOrigin(0.5).setScrollFactor(0).setDepth(DEPTH.HUD);

    // 订阅 store，等待 scene_setup / Subscribe to store and wait for scene_setup
    this.unsubscribe = gameStore.subscribe(() => {
      const s = gameStore.getState();
      if (s.scene_ready && !this.sceneBuilt) {
        this.buildScene(s.current_scene_id);
      }
      if (this.sceneBuilt) {
        this.charManager?.sync(s.characters, s.character_positions);
        if (s.narrative && this.narrativeText) this.narrativeText.setText(s.narrative);
      }
    });

    // 如果已经有 scene_ready（例如热更新后），直接构建
    if (st.scene_ready) {
      this.buildScene(st.current_scene_id);
    }

    // 监听 tick 事件，处理对话 / Listen to tick events for dialogues
    window.addEventListener("tick-event", this.handleTickEvent as EventListener);
    window.addEventListener("dialogue-replay", this.handleTickEvent as EventListener);
  }

  /** 处理 tick 事件 / Handle tick event */
  private handleTickEvent = (e: CustomEvent): void => {
    const { type, payload } = e.detail;

    // 新 tick 开始：清空上一 tick 未播完的对话，避免队列无限累积
    if (type === "dm_create") {
      if (this.dialogueTimer) window.clearTimeout(this.dialogueTimer);
      this.dialogueTimer = undefined;
      this.dialogueQueue = [];
      this.isPlayingDialogue = false;
      this.dialoguesThisTick = 0;
      this.charManager?.clearBubbles();
      return;
    }

    if (type !== "pc_talk") return;
    // 每 tick 只把第一个 talk 事件做成头顶泡泡，其余仅保留在事件列表
    if (this.dialoguesThisTick >= this.MAX_DIALOGUE_EVENTS_PER_TICK) return;
    this.dialoguesThisTick++;
    const result = payload?.result as Record<string, unknown> | undefined;
    const turns = result?.turns as Array<{ speaker_id: string; text: string }> | undefined;
    if (!turns?.length) return;
    this.dialogueQueue.push(...turns);
    this.playNextDialogue();
  };

  /** 播放队列中下一句对话 / Play next dialogue in queue */
  private playNextDialogue(): void {
    if (this.isPlayingDialogue || this.dialogueQueue.length === 0) return;
    this.isPlayingDialogue = true;
    const turn = this.dialogueQueue.shift()!;
    const sprite = this.charManager?.getSprite(turn.speaker_id);
    const advance = () => {
      this.isPlayingDialogue = false;
      this.playNextDialogue();
    };
    if (sprite) {
      sprite.say(turn.text, advance);
    } else if (!this.sceneBuilt) {
      // 场景尚未构建完成，稍等重试 / Scene not ready yet, retry shortly
      this.dialogueTimer = window.setTimeout(() => {
        this.dialogueQueue.unshift(turn);
        this.isPlayingDialogue = false;
        this.playNextDialogue();
      }, 200);
    } else {
      console.warn("[Scene] dialogue speaker not found:", turn.speaker_id);
      // 找不到说话者时短暂停留后继续 / Brief pause if speaker missing
      this.dialogueTimer = window.setTimeout(advance, 600);
    }
  }

  /** 构建实际游戏场景 / Build the actual game scene */
  private buildScene(sceneId: string): void {
    if (this.sceneBuilt) return;
    this.sceneBuilt = true;

    // 移除等待文本 / Remove waiting text
    if (this.waitingText) {
      this.waitingText.destroy();
      this.waitingText = null;
    }

    const st = gameStore.getState();
    this.mapKey = st.current_map_key || KEY.TILEMAP.TUXEMON;

    this.initCamera();
    this.initPhysics();
    this.createBackground();
    this.createGroups();
    this.createLevel();
    this.createTerrain();
    this.createPlayer();
    this.createEnemies();
    this.initAnimations();
    this.initInput();
    this.setupCollisions();
    this.createUI();

    this.cameras.main.fadeIn(400, 0, 0, 0);
    console.log("[Scene] buildScene scene_id=%s map=%s", sceneId, this.mapKey);
  }

  /** 1. initCamera / Camera config */
  private initCamera(): void {
    // setBounds 在 createLevel 中执行（需 tilemap 尺寸）
  }

  /** 2. initPhysics / Physics world — TODO: PMove 实时操控时启用 */
  private initPhysics(): void {
    // 当前跳过：kb/18 "Skip Physics When: Grid-based movement"
  }

  /** 3. createBackground / Background visuals */
  private createBackground(): void {
    this.tilemap = this.make.tilemap({ key: this.mapKey });
    const tsImageKey = this.mapKey === KEY.TILEMAP.DESERT ? KEY.IMAGE.DESERT : KEY.IMAGE.TUXEMON;
    const tsName = this.mapKey === KEY.TILEMAP.DESERT ? "Desert" : TILEMAP.TILESET_NAME;
    const tileset = this.tilemap.addTilesetImage(tsName, tsImageKey);
    if (!tileset) { console.error("[Scene] tileset FAIL for", this.mapKey); return; }
    this.tilemap.createLayer(TILEMAP.LAYERS.BELOW, tileset, 0, 0);
    console.log("[Scene] createBackground map=", this.mapKey);
  }

  /** 4. createGroups / Physics groups — TODO: 对象池化频繁创建的对象 */
  private createGroups(): void {
    // 当前跳过：无 physics groups
  }

  /** 5. createLevel / Static objects: World + Above layers + collision props */
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

  /** 6. createTerrain / 场景物品渲染 */
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

  /** 12. createUI / HUD overlay */
  private createUI(): void {
    const st = gameStore.getState();
    const scene = st.scenes.find((s) => s.id === st.current_scene_id);
    this.sceneNameText = this.add.text(8, 4, `${scene?.name || ""}`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setScrollFactor(0).setDepth(DEPTH.HUD);

    this.narrativeText = this.add.text(10, CONFIG.CANVAS.height - 40,
      "",
      { fontFamily: "Segoe UI, sans-serif", fontSize: "13px", color: "#ffd700",
        backgroundColor: "rgba(0,0,0,0.7)", padding: { x: 10, y: 6 } },
    ).setScrollFactor(0).setDepth(DEPTH.HUD);

    console.log("[Scene] createUI done");
  }

  /** 场景切换 / Switch scene */
  private onSceneChanged(sceneId: string): void {
    const nextMapKey = gameStore.getState().current_map_key;
    if (!nextMapKey || nextMapKey === this.mapKey) return;
    console.log("[Scene] scene-changed →", sceneId, "restarting with", nextMapKey);
    this.cameras.main.fadeOut(400, 0, 0, 0);
    this.cameras.main.once("camerafadeoutcomplete", () => {
      this.scene.start("Game", { mapKey: nextMapKey });
    });
  }

  setNarrative(text: string): void {
    if (this.narrativeText) this.narrativeText.setText(text);
  }

  shutdown(): void {
    window.removeEventListener("tick-event", this.handleTickEvent as EventListener);
    window.removeEventListener("dialogue-replay", this.handleTickEvent as EventListener);
    if (this.dialogueTimer) window.clearTimeout(this.dialogueTimer);
    this.dialogueQueue = [];
    if (this.unsubscribe) this.unsubscribe();
    this.charManager?.destroy();
  }
}
