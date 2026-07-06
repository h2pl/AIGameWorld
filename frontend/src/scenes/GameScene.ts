/** 主游戏场景 / Main Game Scene — 纯编排，所有数据从事件来 */
import Phaser from "phaser";
import { worldStore } from "../state/WorldStore";
import { CONFIG } from "../config";
import { DEPTH, TILEMAP } from "../constants";
import { gridToWorld } from "../utils/tile";
import { makeCharTexture, makeObjectTexture } from "../utils/textures";
import { MapManager } from "../managers/MapManager";
import { PcManager } from "../managers/PcManager";
import { ActorManager } from "../managers/ActorManager";
import { MovementManager } from "../managers/MovementManager";
import { EventManager } from "../managers/EventManager";
import { ExploreHandler } from "../managers/event_handler/ExploreHandler";
import { TalkHandler } from "../managers/event_handler/TalkHandler";
import { NarrativeHandler } from "../managers/event_handler/NarrativeHandler";
import { InteractHandler } from "../managers/event_handler/InteractHandler";
import {
  SceneSetupHandler,
  type SceneSetupData,
} from "../managers/event_handler/SceneSetupHandler";
import { GameHUD } from "../ui/GameHUD";
import { createLogger } from "../utils/logger";

const log = createLogger("Scene");

export class GameScene extends Phaser.Scene {
  private ts!: number;
  private pcManager!: PcManager;
  private actorManager!: ActorManager;
  private movementManager!: MovementManager;
  private mapManager!: MapManager;
  private hud!: GameHUD;
  private eventManager!: EventManager;
  private terrainSprites: Phaser.GameObjects.Sprite[] = [];
  private sceneBuilt = false;
  private sceneData: SceneSetupData | null = null;

  private exploreHandler!: ExploreHandler;
  private talkHandler!: TalkHandler;
  private narrativeHandler!: NarrativeHandler;
  private interactHandler!: InteractHandler;
  private sceneSetupHandler!: SceneSetupHandler;

  constructor() {
    super({ key: "Game" });
  }

  /** Phaser 创建生命周期 / Phaser create lifecycle */
  create(): void {
    this.ts = TILEMAP.TILE_SIZE;
    this.mapManager = new MapManager(this);
    this.hud = new GameHUD(this);
    this.cameras.main.setBackgroundColor("#000000");

    // 预生成角色纹理 / Pre-generate character textures
    for (const fb of [
      { id: "fighter_fb", race: "human", role: "fighter", is_pc: true },
      { id: "actor_fb", race: "human", role: "villager", is_pc: false },
    ]) {
      makeCharTexture(this, fb, this.ts);
    }

    this.hud.showWaiting("等待 DM 创造情境...");
    this.eventManager = this.game.registry.get("eventManager") as EventManager;
    this._initHandlers();
    this._registerHandlers();
    this.game.events.on("scene-reset", () => this._destroyScene());
    this._recoverFromReload();
  }

  /** 场景销毁 / Scene shutdown */
  shutdown(): void {
    this.talkHandler?.clear();
    this.pcManager?.destroy();
    this.actorManager?.destroy();
    this.game.events.off("scene-reset");
  }

  /** 确保场景已构建，scene_id 变化时自动切换 / Ensure scene built, auto-switch on change */
  ensureScene(data: SceneSetupData): void {
    const curId = worldStore.getState().current_scene_id;
    if (this.sceneBuilt && curId === data.sceneId) return;
    if (this.sceneBuilt) {
      log.info(`switch: ${curId} → ${data.sceneId}`);
      this._destroyScene();
    }
    this._buildScene(data);
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
    this.sceneSetupHandler = new SceneSetupHandler((d) => this.ensureScene(d));
  }

  /** 注册事件类型映射 / Register event type → handler */
  private _registerHandlers(): void {
    if (!this.eventManager) return;
    this.eventManager.register("scene_setup", (ev) => this.sceneSetupHandler.handle(ev));
    this.eventManager.register("pc_explore", (ev) => this.exploreHandler.handle(ev));
    this.eventManager.register("pc_talk", (ev) => this.talkHandler.handle(ev));
    this.eventManager.register("pc_interact", (ev) => this.interactHandler.handle(ev));
    this.eventManager.register("dm_narrative", (ev) => this.narrativeHandler.handle(ev));
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

    log.info(
      `build scene=${data.sceneId} map=${data.mapKey} pcs=${data.pcs.length} actors=${data.actors.length}`
    );
    try {
      this.mapManager.build(data.mapKey, data.extJson);
      this._buildTerrain(data.sceneObjects);
      this._buildCharacters(data.pcs, data.actors);
      this.hud.create(data.sceneName);
      this._setupInput();
      this.cameras.main.fadeIn(400, 0, 0, 0);
    } catch (e) {
      log.error(`build ERROR:`, e);
    }
  }

  /** 构建场景物体 / Build terrain objects */
  private _buildTerrain(objects: any[]): void {
    this.terrainSprites = [];
    for (const obj of objects) {
      const key = `obj_${obj.id}`;
      if (!this.textures.exists(key)) makeObjectTexture(this, obj, key, this.ts);
      const { wx, wy } = gridToWorld(obj.position_x, obj.position_y, this.ts);
      this.terrainSprites.push(
        this.add
          .sprite(wx, wy, key)
          .setOrigin(0.5, 1)
          .setDepth(DEPTH.CHARACTER - 1)
          .setInteractive({ useHandCursor: true })
          .on("pointerdown", () =>
            document.dispatchEvent(new CustomEvent("object-interacted", { detail: obj }))
          )
      );
    }
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
    // 相机滚动仅基于 PC / Camera scroll based on PCs only
    const { sx, sy } = this.pcManager.calcCameraScroll(CONFIG.CANVAS.width, CONFIG.CANVAS.height);
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
    this.pcManager?.destroy();
    this.pcManager = undefined as any;
    this.actorManager?.destroy();
    this.actorManager = undefined as any;
    this.mapManager.destroy();
    this.terrainSprites.forEach((s) => {
      if (s.active) s.destroy();
    });
    this.terrainSprites = [];
    this.hud.destroy();
    this.talkHandler?.clear();
    this.cameras.main.setBounds(0, 0, CONFIG.CANVAS.width, CONFIG.CANVAS.height);
    this.cameras.main.scrollX = 0;
    this.cameras.main.scrollY = 0;
    this.cameras.main.fadeIn(0);
    this.hud.showWaiting("等待 DM 创造情境...");
  }
}
