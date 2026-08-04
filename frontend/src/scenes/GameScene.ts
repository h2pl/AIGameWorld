/** 主游戏场景 / Main Game Scene — 纯编排，所有数据从事件来 */
import Phaser from "phaser";
import { worldStore } from "../state/WorldStore";
import { CONFIG } from "../config";
import { DEPTH, TILEMAP } from "../constants";
import { gridToWorld } from "../utils/tile";
import { makeCharTexture, makeObjectTexture } from "../utils/textures";
import { BGMPlayer } from "../utils/BGMPlayer";
import { MapManager } from "../managers/MapManager";
import { PcManager } from "../managers/PcManager";
import { ActorManager } from "../managers/ActorManager";
import { MovementManager } from "../managers/MovementManager";
import { EventManager } from "../managers/EventManager";
import { ExploreHandler } from "../managers/event_handler/ExploreHandler";
import { TalkHandler } from "../managers/event_handler/TalkHandler";
import { NarrativeHandler } from "../managers/event_handler/NarrativeHandler";
import { InteractHandler } from "../managers/event_handler/InteractHandler";
import { CombatHandler } from "../managers/event_handler/CombatHandler";
import { DecisionHandler } from "../managers/event_handler/DecisionHandler";
import { PartyDiscussHandler } from "../managers/event_handler/PartyDiscussHandler";
import { PartyDecideHandler } from "../managers/event_handler/PartyDecideHandler";
import { PartyCampHandler } from "../managers/event_handler/PartyCampHandler";
import {
  SceneSetupHandler,
  type SceneSetupData,
} from "../managers/event_handler/SceneSetupHandler";
import { GameHUD } from "../ui/GameHUD";
import { createLogger } from "../utils/logger";
import type { EventData } from "../types";

const log = createLogger("Scene");

export class GameScene extends Phaser.Scene {
  private ts!: number;
  private pcManager!: PcManager;
  private actorManager!: ActorManager;
  private movementManager!: MovementManager;
  private mapManager!: MapManager;
  private hud!: GameHUD;
  private eventManager!: EventManager;
  private bgm!: BGMPlayer;
  private terrainSprites: Phaser.GameObjects.Sprite[] = [];
  private terrainObjects: any[] = [];
  private sceneBuilt = false;
  private sceneData: SceneSetupData | null = null;
  private _onPlayPaused!: () => void;
  private _onPlayResumed!: () => void;
  private _cameraZoom = 1.0;

  private exploreHandler!: ExploreHandler;
  private talkHandler!: TalkHandler;
  private narrativeHandler!: NarrativeHandler;
  private interactHandler!: InteractHandler;
  private combatHandler!: CombatHandler;
  private decisionHandler!: DecisionHandler;
  private sceneSetupHandler!: SceneSetupHandler;
  private partyDiscussHandler!: PartyDiscussHandler;
  private partyDecideHandler!: PartyDecideHandler;
  private partyCampHandler!: PartyCampHandler;

  constructor() {
    super({ key: "Game" });
  }

  /** Phaser 创建生命周期 / Phaser create lifecycle */
  create(): void {
    this.ts = TILEMAP.TILE_SIZE;
    this.mapManager = new MapManager(this);
    this.hud = new GameHUD(this);
    this.cameras.main.setBackgroundColor("#000000");

    this.hud.showWaiting("等待 DM 创造情境...");
    this.eventManager = this.game.registry.get("eventManager") as EventManager;
    this._initHandlers();
    this._registerHandlers();
    this.game.events.on("scene-reset", () => this._handleReset());
    // 播放暂停/恢复时同步 tween 状态 / Sync tween state on pause/resume
    this._onPlayPaused = () => this.tweens.pauseAll();
    this._onPlayResumed = () => this.tweens.resumeAll();
    window.addEventListener("play-paused", this._onPlayPaused);
    window.addEventListener("play-resumed", this._onPlayResumed);
    // tick=0 时不应构建场景，等待 scene_setup 事件驱动 / Don't build scene at tick=0, wait for scene_setup event
    this._recoverFromReload();
    this._initTestSeam();
  }

  /** 初始化浏览器测试 seam / Init browser test seam for E2E */
  private _initTestSeam(): void {
    (window as any).__TEST__ = {
      ready: true,
      sceneKey: "Game",
      sceneBuilt: false,
      gameState: () => this._getTestState(),
      clickObject: (idx: number) => {
        const obj = this.terrainObjects[idx];
        if (obj) this._onObjectClick(obj);
      },
    };
  }

  /** 返回可序列化的游戏状态快照 / Return serializable game state snapshot */
  private _getTestState(): Record<string, unknown> {
    const state = worldStore.getState();
    const pcThinkCounts: Record<string, number> = {};
    let activeThoughtBubbles = 0;
    const pcPositions: Record<string, { tx: number; ty: number }> = {};
    const pcWalking: Record<string, boolean> = {};
    const pcBubbleStyle: Record<string, string | null> = {};
    this.pcManager?.sprites.forEach((sp, id) => {
      pcThinkCounts[id] = sp.getThinkCount();
      if (sp.hasActiveThoughtBubble()) activeThoughtBubbles++;
      pcPositions[id] = sp.getGridPos(this.ts);
      pcWalking[id] = sp.isWalking();
      pcBubbleStyle[id] = sp.getActiveBubbleStyle();
    });
    const actorPositions: Record<string, { tx: number; ty: number }> = {};
    const actorExists: Record<string, boolean> = {};
    this.actorManager?.sprites.forEach((sp, id) => {
      actorPositions[id] = sp.getGridPos(this.ts);
      actorExists[id] = true;
    });
    return {
      scene: "Game",
      sceneBuilt: this.sceneBuilt,
      sceneId: this.sceneData?.sceneId ?? null,
      sceneName: this.sceneData?.sceneName ?? null,
      pcCount: this.pcManager?.sprites.size ?? 0,
      actorCount: this.actorManager?.sprites.size ?? 0,
      displayTick: state.display_tick,
      worldId: state.world_id,
      pcThinkCounts,
      activeThoughtBubbles,
      terrainObjectCount: this.terrainObjects.length,
      cameraZoom: this._cameraZoom,
      pcPositions,
      pcWalking,
      pcBubbleStyle,
      actorPositions,
      actorExists,
    };
  }

  /** 场景销毁 / Scene shutdown */
  shutdown(): void {
    this.talkHandler?.clear();
    this.pcManager?.destroy();
    this.actorManager?.destroy();
    this.game.events.off("scene-reset");
    window.removeEventListener("play-paused", this._onPlayPaused);
    window.removeEventListener("play-resumed", this._onPlayResumed);
  }

  /** 确保场景已构建 + 等待渲染就绪 / Ensure scene built + wait for render ready */
  async ensureScene(data: SceneSetupData): Promise<void> {
    const curId = worldStore.getState().current_scene_id;
    if (this.sceneBuilt && curId === data.sceneId) return;
    if (this.sceneBuilt) {
      log.info(`switch: ${curId} → ${data.sceneId}`);
      this._destroyScene();
    }
    this._buildScene(data);
    // 等 3 帧确保 Phaser 完成精灵渲染 / Wait 3 frames for Phaser rendering
    for (let i = 0; i < 3; i++) {
      await new Promise((r) => this.time.delayedCall(16, r));
    }
  }

  /** 销毁当前场景 / Destroy current scene */
  destroyScene(): void {
    this._destroyScene();
  }

  /** 初始化事件处理器 / Init all event handlers */
  private _initHandlers(): void {
    const follow = (sprite: any) => this.cameras.main.startFollow(sprite, true, 0.1, 0.1);
    const getSprite = (id: string) =>
      this.pcManager?.getSprite(id) || this.actorManager?.getSprite(id);
    this.exploreHandler = new ExploreHandler(
      getSprite,
      () => this.movementManager,
      follow,
      () => this
    );
    this.talkHandler = new TalkHandler(
      getSprite,
      () => this.movementManager,
      () => this.sceneBuilt,
      follow
    );
    this.narrativeHandler = new NarrativeHandler();
    this.interactHandler = new InteractHandler(getSprite, () => this.movementManager, follow);
    this.combatHandler = new CombatHandler(
      getSprite,
      () => this.movementManager,
      () => this.actorManager,
      follow
    );
    this.decisionHandler = new DecisionHandler(getSprite, follow);
    this.sceneSetupHandler = new SceneSetupHandler((d) => this.ensureScene(d));
    const getAnySprite = (): any => {
      const it = this.pcManager?.sprites.values().next();
      return it && !it.done ? it.value : undefined;
    };
    this.partyDiscussHandler = new PartyDiscussHandler(
      getSprite,
      getAnySprite,
      () => this.movementManager,
      follow
    );
    this.partyDecideHandler = new PartyDecideHandler(getAnySprite);
    this.partyCampHandler = new PartyCampHandler(
      getSprite,
      getAnySprite,
      () => this.movementManager,
      follow
    );
  }

  /** 注册事件类型映射 / Register event type → handler */
  private _registerHandlers(): void {
    if (!this.eventManager) return;
    this.eventManager.register("scene_setup", (ev) => this.sceneSetupHandler.handle(ev));
    this.eventManager.register("pc_decision", (ev) => this.decisionHandler.handle(ev));
    this.eventManager.register("pc_explore", (ev) => this.exploreHandler.handle(ev));
    this.eventManager.register("pc_talk", (ev) => this.talkHandler.handle(ev));
    this.eventManager.register("pc_interact", (ev) => this.interactHandler.handle(ev));
    this.eventManager.register("pc_combat", (ev) => this.combatHandler.handle(ev));
    this.eventManager.register("dm_narrative", (ev) => this.narrativeHandler.handle(ev));
    this.eventManager.register("party_discuss", (ev) => this.partyDiscussHandler.handle(ev));
    this.eventManager.register("party_decide", (ev) => this.partyDecideHandler.handle(ev));
    this.eventManager.register("party_camp", (ev) => this.partyCampHandler.handle(ev));
    this.eventManager.register("dm_create", (ev) => this._handleDmCreate(ev));
  }

  /** 重置后销毁场景，回到黑屏等待 / Destroy scene, back to black screen */
  private _handleReset(): void {
    this._destroyScene();
    this.hud = new GameHUD(this);
    this.hud.showWaiting("等待 DM 创造情境...");
    this.cameras.main.setBackgroundColor("#000000");
  }

  /** dm_create 事件：等待面板 fade-in 动画完成 / Wait for panel fade-in to settle */
  private async _handleDmCreate(_ev: EventData): Promise<void> {
    // DMCreationPanel 用 50ms setTimeout + CSS fade-in，等待 1s 确保显示完毕
    await new Promise((r) => setTimeout(r, 1000));
  }

  /** 热重载恢复 / Recover from hot-reload */
  private _recoverFromReload(): void {
    const displayTick = this.game.registry.get("displayTick") as number;
    if (!displayTick || displayTick <= 0) return;
    const player = this.game.registry.get("tickPlayer") as {
      recoverFromReload: (t: number) => Promise<void>;
    };
    if (!player) return;
    this.time.delayedCall(0, () => player.recoverFromReload(displayTick));
  }

  /** 构建完整场景 / Build complete scene */
  private _buildScene(data: SceneSetupData): void {
    if (this.sceneBuilt) return;
    this.sceneBuilt = true;
    this.sceneData = data;
    this.hud.hideWaiting();

    // 启动背景音乐 / Start background music
    this.bgm = new BGMPlayer();
    this.bgm.play().catch(() => {});

    log.info(`build scene=${data.sceneId} pcs=${data.pcs.length} actors=${data.actors.length}`);
    // 从 ext_json 读取 tile_size，覆盖默认值
    this.ts = Number(data.extJson.tile_size) || TILEMAP.TILE_SIZE;

    // 按真实 tile_size 预生成角色回退纹理 / Pre-generate fallback textures at correct tile_size
    for (const fb of [
      { id: "fighter_fb", race: "human", role: "fighter", is_pc: true },
      { id: "actor_fb", race: "human", role: "villager", is_pc: false },
    ]) {
      makeCharTexture(this, fb, this.ts);
    }

    try {
      const { mapW, mapH } = this.mapManager.build(data.sceneId, data.extJson);
      // 动态缩放：小地图拉近距离，所有地图视觉大小一致 / Dynamic zoom: small maps get closer camera
      const canvas = CONFIG.CANVAS;
      const rawZoom = Math.min(canvas.width / mapW, canvas.height / mapH);
      this._cameraZoom = Math.max(1.0, Math.min(rawZoom, 2.5));
      this.cameras.main.setZoom(this._cameraZoom);
      log.info(
        `camera zoom=%.2f (map=%dx%d canvas=%dx%d)`,
        this._cameraZoom,
        mapW,
        mapH,
        canvas.width,
        canvas.height
      );

      this._buildTerrain(data.sceneObjects);
      this._buildCharacters(data.pcs, data.actors);
      this.hud.create(data.sceneName);
      this._setupInput();
      this.cameras.main.fadeIn(400, 0, 0, 0);
      const test = (window as any).__TEST__;
      if (test) test.sceneBuilt = true;
    } catch (e) {
      log.error(`build ERROR:`, e);
    }
  }

  /** 构建场景物体 / Build terrain objects */
  private _buildTerrain(objects: any[]): void {
    this.terrainSprites = [];
    this.terrainObjects = [];
    for (const obj of objects) {
      const key = `obj_${obj.id}`;
      if (!this.textures.exists(key)) makeObjectTexture(this, obj, key, this.ts);
      const { wx, wy } = gridToWorld(obj.position_x, obj.position_y, this.ts);
      this.terrainObjects.push(obj);
      this.terrainSprites.push(
        this.add
          .sprite(wx, wy, key)
          .setOrigin(0.5, 1)
          .setDepth(DEPTH.CHARACTER - 1)
          .setInteractive({ useHandCursor: true })
          .on("pointerdown", () => this._onObjectClick(obj))
      );
    }
  }

  /** 场景物体点击处理 / Scene object click handler */
  private _onObjectClick(obj: any): void {
    document.dispatchEvent(new CustomEvent("object-interacted", { detail: obj }));
  }

  /** 构建角色精灵 + 相机 / Build character sprites + camera */
  private _buildCharacters(pcs: any[], actors: any[]): void {
    this.pcManager = new PcManager(this, this.ts);
    this.actorManager = new ActorManager(this, this.ts);
    this.movementManager = new MovementManager(this, this.ts);
    for (const pc of pcs) makeCharTexture(this, pc, this.ts);
    for (const actor of actors) makeCharTexture(this, actor, this.ts);
    this.pcManager.createAll(pcs);
    if (actors.length) this.actorManager.createAll(actors);
    log.info(`buildChars: pcs=${pcs.length} actors=${actors.length}`);
    // 相机滚动仅基于 PC / Camera scroll based on PCs only (visible area = canvas / zoom)
    const { sx, sy } = this.pcManager.calcCameraScroll(
      CONFIG.CANVAS.width / this._cameraZoom,
      CONFIG.CANVAS.height / this._cameraZoom
    );
    this.cameras.main.scrollX = sx;
    this.cameras.main.scrollY = sy;
  }

  /** 点击选角 / Click-to-select character */
  private _setupInput(): void {
    const d = this.sceneData!;
    this.input.on("pointerdown", (p: Phaser.Input.Pointer) => {
      const wp = this.cameras.main.getWorldPoint(p.x, p.y);
      for (const pc of d.pcs) {
        if (
          Math.abs(wp.x - (pc.position_x * this.ts + this.ts / 2)) < 20 &&
          Math.abs(wp.y - (pc.position_y * this.ts + this.ts / 2)) < 20
        ) {
          document.dispatchEvent(new CustomEvent("character-selected", { detail: pc }));
          return;
        }
      }
      for (const actor of d.actors) {
        if (
          Math.abs(wp.x - (actor.position_x * this.ts + this.ts / 2)) < 20 &&
          Math.abs(wp.y - (actor.position_y * this.ts + this.ts / 2)) < 20
        ) {
          document.dispatchEvent(new CustomEvent("character-selected", { detail: actor }));
          return;
        }
      }
    });
  }

  /** 销毁当前场景所有对象 / Destroy all scene objects */
  private _destroyScene(): void {
    this.sceneBuilt = false;
    const test = (window as any).__TEST__;
    if (test) test.sceneBuilt = false;
    this.bgm?.stop();
    this.pcManager?.destroy();
    this.pcManager = undefined as any;
    this.actorManager?.destroy();
    this.actorManager = undefined as any;
    this.mapManager.destroy();
    this.terrainSprites.forEach((s) => {
      if (s.active) s.destroy();
    });
    this.terrainSprites = [];
    this.terrainObjects = [];
    this.hud.destroy();
    this.talkHandler?.clear();
    this.cameras.main.setBounds(0, 0, CONFIG.CANVAS.width, CONFIG.CANVAS.height);
    this.cameras.main.setZoom(1.0);
    this._cameraZoom = 1.0;
    this.cameras.main.scrollX = 0;
    this.cameras.main.scrollY = 0;
    this.cameras.main.fadeIn(0);
    this.hud.showWaiting("等待 DM 创造情境...");
  }
}
