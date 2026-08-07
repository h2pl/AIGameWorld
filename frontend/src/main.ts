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
import { MetricsPanel } from "./ui/MetricsPanel";
import { ControlBar } from "./ui/ControlBar";
import "./ui/styles.css";
import { showWorldSelectionIfNeeded } from "./EntryScreen";
import { createLogger } from "./utils/logger";
const log = createLogger("Main");

async function main(): Promise<void> {
  log.info(`=== START ===`);

  // ── 0. 入口选择：无 ?world= 时展示世界选择页并等待选择 ──
  // 选择后会带 ?world=<id> reload，此调用在 URL 无 world 时阻塞（页面 reload），不返回。
  const hasWorld = new URLSearchParams(window.location.search).has("world");
  if (!hasWorld) {
    await showWorldSelectionIfNeeded();
  }

  // ── 1. Bootstrap ──
  const { world } = await bootstrap();
  worldStore.setWorldState(world.world_id, world.llm_mock, world.data_mode, world.db_name);
  // 同步后端 display_tick 到 store，避免首次进入显示 0
  worldStore.setDisplayTick(world.display_tick || 0);
  // 场景列表在 Phaser 之前写入，避免 registry 时序问题 / Set scene list before Phaser
  const { setSceneList } = await import("./state/SceneList");
  setSceneList(world.scenes);

  // ── 2. App 容器 ──
  const app = document.getElementById("app")!;

  // ── 3. Phaser ──
  const { EventManager } = await import("./managers/EventManager");
  const { TickPlayer } = await import("./TickPlayer");
  const eventManager = new EventManager();
  const player = new TickPlayer(
    CONFIG.API.base,
    world.world_id,
    eventManager,
    world.display_tick || 0
  );
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    width: CONFIG.CANVAS.width,
    height: CONFIG.CANVAS.height,
    autoFocus: true,
    backgroundColor: CONFIG.COLOR.background,
    // 参考本地权威 Phaser 项目（SkyOffice / phaser-rpg / reldens）全部用 pixelArt:true 保持地图像素硬边，
    // 而 SkyOffice（唯一与我们场景完全对应：角色头顶名字+对话泡泡）用 Scale.RESIZE 让画布 1:1 跟随窗口，
    // 文本按真实像素光栅化、天然清晰，无需任何 resolution 补丁。
    // FIT 会把 960 基准画布放大到窗口，是文本发糊的根因，故改用 RESIZE。
    pixelArt: true,
    roundPixels: false,
    physics: { default: "arcade", arcade: { gravity: { x: 0, y: 0 }, debug: false } },
    // RESIZE：画布尺寸 = 窗口尺寸，1:1 无放大，文本/地图均清晰；GameScene 监听 resize 重算相机
    scale: {
      mode: Phaser.Scale.RESIZE,
      autoCenter: Phaser.Scale.CENTER_BOTH,
      width: window.innerWidth,
      height: window.innerHeight,
    },
    scene: [Boot, GameScene],
  });
  game.registry.set("eventManager", eventManager);
  game.registry.set("tickPlayer", player);
  game.registry.set("displayTick", world.display_tick || 0);
  game.registry.set("initialWorldState", world);

  // ── 4. DOM 面板 ──
  new DMCreationPanel().mount(app);
  new NarrativePanel().mount(app);
  new EventPanel().mount(app);
  new CharacterPanel().mount(app);
  new ObjectPanel().mount(app);
  new MockConfigPanel().mount(app);
  const metricsPanel = new MetricsPanel();
  metricsPanel.mount(app);
  const historyPanel = new HistoryEventPanel(world.world_id);
  historyPanel.mount(app);
  window.addEventListener("show-event-history", () =>
    historyPanel.open(worldStore.getState().display_tick)
  );

  // ── 5. 控制栏 ──
  const bar = new ControlBar();
  bar.mount(app);
  bar.initReady(true);

  // ── 6. TickPlayer ──
  const displayTick = world.display_tick || 0;
  const dataTick = world.data_tick || 0;
  if (displayTick > 0) {
    bar.setTickDisplay(displayTick);
  } else if (dataTick > 0) {
    // 已生成 tick 但前端未播放：提示可跳转，不自动播放 / Generated but not displayed yet
    bar.setStatus(`已生成 ${dataTick} 个 tick，可跳转`);
  } else {
    bar.setTickDisplay(0);
  }

  const onTickCallback = (tick: number) => {
    worldStore.setDisplayTick(tick);
    bar.setTickDisplay(tick);
  };

  bar.setCallbacks({
    getTickCount: () => player.lastTick,
    onRun: async (n) => {
      await player.runTicks(n, onTickCallback);
    },
    onStart: async () => player.startLoop(onTickCallback),
    onPause: async () => player.pauseLoop(),
    onResume: async () => player.resumeLoop(onTickCallback),
    onJump: async (t) => {
      await player.jumpTo(t, onTickCallback);
    },
    onReset: async () => {
      await player.reset();
      worldStore.clear();
      game.events.emit("scene-reset");
      bar.setTickDisplay(0);
      window.dispatchEvent(new CustomEvent("tick-start", { detail: { tick: 0 } }));
    },
    onExit: () => {
      // 退出到世界选择页：清空当前世界状态，跳到无 ?world= 的根路径，重新进入入口页 /
      // Exit to world selection: clear state and navigate to root (re-triggers entry page)
      player.stop();
      worldStore.clear();
      window.location.href = window.location.origin + window.location.pathname;
    },
  });

  log.info(`=== READY, world_id=${world.world_id} ===`);
}

main();
