/** AIGameWorld 前端入口 / Frontend entry point */
const L = "[Main]";
import Phaser from "phaser";
import { Boot } from "./scenes/Boot";
import { GameScene } from "./scenes/GameScene";
import { CONFIG } from "./config";
import { bootstrap } from "./bootstrap";
import { worldStore } from "./state/WorldStore";
import { tickStore } from "./state/TickStore";
import { NarrativePanel } from "./ui/NarrativePanel";
import { EventPanel } from "./ui/EventPanel";
import { DMCreationPanel } from "./ui/DMCreationPanel";
import { CharacterPanel } from "./ui/CharacterPanel";
import { ObjectPanel } from "./ui/ObjectPanel";
import { HistoryEventPanel } from "./ui/HistoryEventPanel";
import { MockConfigPanel } from "./ui/MockConfigPanel";
import { ControlBar } from "./ui/ControlBar";
import "./ui/styles.css";

async function main(): Promise<void> {
  console.log(`${L} === START ===`);

  // ── 1. Bootstrap ──
  const { world } = await bootstrap();
  worldStore.setWorldState(
    world.world_id,
    world.scenes,
    world.characters,
    world.items,
    world.scene_objects,
    world.llm_mock,
    world.data_mode,
    world.db_name
  );
  console.log(`${L} stores ready: ${world.scenes.length} scenes, ${world.characters.length} chars`);

  // ── 2. App 容器 / App container ──
  const app = document.getElementById("app")!;

  // ── 3. Phaser ──
  const { EventManager } = await import("./managers/EventManager");
  const eventManager = new EventManager();
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    width: CONFIG.CANVAS.width,
    height: CONFIG.CANVAS.height,
    autoFocus: true,
    backgroundColor: CONFIG.COLOR.background,
    pixelArt: true,
    roundPixels: true,
    physics: { default: "arcade", arcade: { gravity: { x: 0, y: 0 }, debug: false } },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    scene: [Boot, GameScene],
  });
  game.registry.set("eventManager", eventManager);

  // ── 4. DOM 面板 / Dom panels ──
  new DMCreationPanel().mount(app);
  new NarrativePanel().mount(app);
  new EventPanel().mount(app);
  new CharacterPanel().mount(app);
  new ObjectPanel().mount(app);
  new MockConfigPanel().mount(app);

  const historyPanel = new HistoryEventPanel(world.world_id);
  historyPanel.mount(app);
  window.addEventListener("show-event-history", () => {
    historyPanel.open(tickStore.getState().display_tick);
  });

  // 叙事转发 / Narrative relay
  const relay = () => {
    const s = { ...worldStore.getState(), ...tickStore.getState() } as any;
    const gs = game.scene.scenes.find((sc) => sc.scene.key === "Game") as any;
    if (gs?.setNarrative && s.narrative) gs.setNarrative(s.narrative);
  };
  worldStore.subscribe(relay);
  tickStore.subscribe(relay);

  // ── 5. 控制栏 / Control bar ──
  const bar = new ControlBar();
  bar.mount(app);
  bar.initReady(true);

  // ── 6. TickPlayer ──
  const { TickPlayer } = await import("./managers/TickPlayer");
  const player = new TickPlayer(CONFIG.API.base, world.world_id, eventManager);
  const displayTick = world.display_tick || 0;
  player.setLastTick(displayTick);
  if (displayTick > 0) {
    bar.setStatus(`已展示到 Tick ${displayTick}`);
    await player.loadHistory(displayTick);
  }

  const onTickCallback = (tick: number, events: any[]) => {
    bar.setStatus(`展示 Tick ${tick} (${events.length} events)`);
    tickStore.setDisplayTick(tick);
  };

  bar.setCallbacks({
    getTickCount: () => displayTick,
    onRun: async (n) => {
      await player.runTicks(n, onTickCallback);
    },
    onStart: async () => {
      await player.startLoop(onTickCallback);
    },
    onPause: async () => {
      await player.pauseLoop();
    },
    onResume: async () => {
      await player.resumeLoop(onTickCallback);
    },
    onReset: async () => {
      await player.reset();
      tickStore.clear();
      tickStore.setDisplayTick(0);
    },
  });

  console.log(`${L} === READY, world_id=${world.world_id} ===`);
}

main();
