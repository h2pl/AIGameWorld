/** AIGameWorld 前端入口 / Frontend entry point */
import Phaser from "phaser";
import { Boot } from "./scenes/Boot";
import { GameScene } from "./scenes/GameScene";
import { CONFIG } from "./config";
import { bootstrap } from "./bootstrap";
import { worldStore } from "./state/WorldStore";
import { NarrativePanel } from "./ui/NarrativePanel";
import { EventPanel } from "./ui/EventPanel";
import { DMCreationPanel } from "./ui/DMCreationPanel";
import { CharacterPanel } from "./ui/CharacterPanel";
import { ObjectPanel } from "./ui/ObjectPanel";
import { HistoryEventPanel } from "./ui/HistoryEventPanel";
import { MockConfigPanel } from "./ui/MockConfigPanel";
import { ControlBar } from "./ui/ControlBar";
import "./ui/styles.css";
import { createLogger } from "./utils/logger";
const log = createLogger("Main");

async function main(): Promise<void> {
  log.info(`=== START ===`);

  // ── 1. Bootstrap ──
  const { world } = await bootstrap();
  worldStore.setWorldState(world.world_id, world.llm_mock, world.data_mode, world.db_name);
  // 场景列表在 Phaser 之前写入，避免 registry 时序问题 / Set scene list before Phaser
  const { setSceneList } = await import("./state/SceneList");
  setSceneList(world.scenes);

  // ── 2. App 容器 ──
  const app = document.getElementById("app")!;

  // ── 3. Phaser ──
  const { EventManager } = await import("./managers/EventManager");
  const { TickPlayer } = await import("./TickPlayer");
  const eventManager = new EventManager();
  const player = new TickPlayer(CONFIG.API.base, world.world_id, eventManager);
  const game = new Phaser.Game({
    type: Phaser.AUTO, width: CONFIG.CANVAS.width, height: CONFIG.CANVAS.height,
    autoFocus: true, backgroundColor: CONFIG.COLOR.background,
    pixelArt: true, roundPixels: true,
    physics: { default: "arcade", arcade: { gravity: { x: 0, y: 0 }, debug: false } },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    scene: [Boot, GameScene],
  });
  game.registry.set("eventManager", eventManager);
  game.registry.set("tickPlayer", player);
  game.registry.set("displayTick", world.display_tick || 0);

  // ── 4. DOM 面板 ──
  new DMCreationPanel().mount(app);
  new NarrativePanel().mount(app);
  new EventPanel().mount(app);
  new CharacterPanel().mount(app);
  new ObjectPanel().mount(app);
  new MockConfigPanel().mount(app);
  const historyPanel = new HistoryEventPanel(world.world_id);
  historyPanel.mount(app);
  window.addEventListener("show-event-history", () => historyPanel.open(worldStore.getState().display_tick));

  // ── 5. 控制栏 ──
  const bar = new ControlBar();
  bar.mount(app);
  bar.initReady(true);

  // ── 6. TickPlayer ──
  const displayTick = world.display_tick || 0;
  if (displayTick > 0) bar.setStatus(`已展示到 Tick ${displayTick}`);

  const onTickCallback = (tick: number, events: any[]) => {
    worldStore.setDisplayTick(tick);
    bar.setStatus(`展示 Tick ${tick} (${events.length} events)`);
  };

  bar.setCallbacks({
    getTickCount: () => player.lastTick,
    onRun: async (n) => { await player.runTicks(n, onTickCallback); },
    onStart: async () => player.startLoop(onTickCallback),
    onPause: async () => player.pauseLoop(),
    onResume: async () => player.resumeLoop(onTickCallback),
    onReset: async () => {
      await player.reset();
      worldStore.clear();
      game.events.emit("scene-reset");
      window.dispatchEvent(new CustomEvent("tick-start", { detail: { tick: 0 } }));
    },
  });

  log.info(`=== READY, world_id=${world.world_id} ===`);
}

main();
