/** 主游戏场景 / Main Game Scene — kb/17 初始化顺序 */
import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterManager } from "../managers/CharacterManager";
import { CONFIG } from "../config";
import { KEY, DEPTH, TILEMAP } from "../constants";

export class GameScene extends Phaser.Scene {
  private ts!: number;
  private tilemap!: Phaser.Tilemaps.Tilemap;
  private charManager!: CharacterManager;
  private narrativeText!: Phaser.GameObjects.Text;
  private iconTexts: Phaser.GameObjects.Text[] = [];
  private unsubscribe: (() => void) | null = null;

  constructor() { super({ key: "Game" }); }

  // ══ kb/17 初始化顺序 / Init order ══
  // 完整 21 步，当前跳过的标 TODO

  create(): void {
    this.initVariables();       // 1  ✅
    this.initCamera();          // 2  ✅
    this.initPhysics();         // 3  ⏭️ TODO: PMove 启用时加
    this.createBackground();    // 4  ✅
    this.createGroups();        // 5  ⏭️ TODO: 对象池管理
    this.createLevel();         // 6  ✅
    this.createPlayer();        // 7  ✅ → createCharacters
    this.createEnemies();       // 8  ⏭️ TODO: 战斗系统
    this.initAnimations();      // 9  ⏭️ TODO: spritesheet 动画
    this.initInput();           // 10 ✅
    this.setupCollisions();     // 11 ⏭️ TODO: 战斗碰撞检测
    this.createUI();            // 12 ✅ → 含 store subscribe
  }

  /** 1. initVariables / Reset state */
  private initVariables(): void {
    this.ts = TILEMAP.TILE_SIZE;
    const st = gameStore.getState();
    console.log("[Scene] initVariables ts=%d chars=%d", this.ts, st.characters.length);
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
    this.tilemap = this.make.tilemap({ key: KEY.TILEMAP.TUXEMON });
    const tileset = this.tilemap.addTilesetImage(TILEMAP.TILESET_NAME, KEY.IMAGE.TUXEMON);
    if (!tileset) { console.error("[Scene] tileset FAIL"); return; }
    this.tilemap.createLayer(TILEMAP.LAYERS.BELOW, tileset, 0, 0);
  }

  /** 5. createGroups / Physics groups — TODO: 对象池化频繁创建的对象 */
  private createGroups(): void {
    // 当前跳过：无 physics groups
  }

  /** 6. createLevel / Static objects: World + Above layers + collision props */
  private createLevel(): void {
    const ts = this.tilemap.getTileset(TILEMAP.TILESET_NAME);
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

  /** 12. createUI / HUD overlay + startGame */
  private createUI(): void {
    const st = gameStore.getState();
    const scene = st.scenes[0];
    this.add.text(8, 4, `${scene?.name || "Tuxemon Town"}`, {
      fontFamily: "Segoe UI, sans-serif", fontSize: "12px", color: "#ffd700", fontStyle: "bold",
      backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 },
    }).setScrollFactor(0).setDepth(DEPTH.HUD);

    this.narrativeText = this.add.text(10, CONFIG.CANVAS.height - 40,
      "连接后端后点 [▶] 开始",
      { fontFamily: "Segoe UI, sans-serif", fontSize: "13px", color: "#ffd700",
        backgroundColor: "rgba(0,0,0,0.7)", padding: { x: 10, y: 6 } },
    ).setScrollFactor(0).setDepth(DEPTH.HUD);

    // startGame: 订阅 store（事件驱动，非 update loop）
    this.unsubscribe = gameStore.subscribe(() => {
      const s = gameStore.getState();
      this.charManager.sync(s.characters, s.character_positions);
      if (s.narrative && this.narrativeText) this.narrativeText.setText(s.narrative);
    });

    console.log("[Scene] createUI done, store subscribed");
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
