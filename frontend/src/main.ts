/** AIGameWorld 前端入口 / Frontend entry point — 全链路日志
 *
 * 流程 / Flow:
 *   1. 读取 URL ?pack=xxx 参数 → 2. 调后端 API 获取世界状态
 *   3. API 不可用时用 mock 数据 → 4. 写入 GameStore → 5. 启动 Phaser
 */
const L = "[Main]"; // 日志前缀 / Log prefix
import Phaser from "phaser";
import { Boot } from "./scenes/Boot";
import { GameScene } from "./scenes/GameScene";
import { gameStore } from "./state/GameStore";
import { CONFIG } from "./config";
import type { InitialWorldState } from "./types";
import "./ui/styles.css";
import { NarrativePanel } from "./ui/NarrativePanel";
import { EventPanel } from "./ui/EventPanel";
import { DMCreationPanel } from "./ui/DMCreationPanel";
import { CharacterPanel } from "./ui/CharacterPanel";
import { ObjectPanel } from "./ui/ObjectPanel";

/** 从后端加载初始世界状态 / Load initial world state from backend */
async function loadWorldState(packId: string): Promise<InitialWorldState | null> {
  console.log(`${L} loadWorldState: fetching ${CONFIG.API.base}${CONFIG.API.worldState}/${packId}/state`);
  try {
    const resp = await fetch(`${CONFIG.API.base}${CONFIG.API.worldState}/${packId}/state`);
    if (!resp.ok) {
      console.warn(`${L} API not available (${resp.status}), using mock`);
      return null;
    }
    const data = await resp.json() as InitialWorldState;
    console.log(`${L} API OK: pack=${data.world_id} chars=${data.characters?.length || 0}`);
    return data;
  } catch (e) {
    console.warn(`${L} Backend unreachable, using mock`, e instanceof Error ? e.message : e);
    return null;
  }
}

/** 主入口 / Main entry — 全部数据来自后端，前端不再自带 mock */
async function main(): Promise<void> {
  console.log(`${L} === main() START ===`);
  const params = new URLSearchParams(window.location.search);
  const packId = params.get("pack") || "mock_world";
  console.log(`${L} world_id=${packId}`);

  // 加载世界数据 / Load world data — 全部依赖后端，失败则提示
  let world = await loadWorldState(packId);
  const backendReady = !!world;
  if (!world) {
    console.error(`${L} backend unreachable, rendering UI with disabled controls`);
    world = {
      world_id: packId,
      data_tick: 0,
      display_tick: 0,
      llm_mock: false,
      data_mode: "unknown",
      db_name: "unknown",
      mock_dataset: "",
      scenes: [],
      characters: [],
      items: [],
      scene_objects: [],
    };
  }
  console.log(`${L} world loaded: ${world.scenes.length} scenes, ${world.characters.length} chars`);
  gameStore.setWorldState(
    world.world_id,
    world.scenes,
    world.characters,
    world.items,
    world.scene_objects,
    {
      llm_mock: world.llm_mock ?? false,
      data_mode: world.data_mode ?? "real",
      db_name: world.db_name ?? "world_db.db",
      mock_dataset: world.mock_dataset ?? "",
    },
  );
  console.log(`${L} store initialized`);

  // 启动 Phaser 游戏引擎 / Start Phaser game engine
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    width: CONFIG.CANVAS.width,
    height: CONFIG.CANVAS.height,
    autoFocus: true,
    backgroundColor: CONFIG.COLOR.background,
    pixelArt: true,
    roundPixels: true,
    physics: {
      default: "arcade",
      arcade: {
        gravity: { x: 0, y: 0 },
        debug: false,
      },
    },
    scale: {
      mode: Phaser.Scale.FIT,
      autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    scene: [Boot, GameScene],
  });
  console.log(`${L} Phaser.Game created, scenes: Boot → Game`);

  // ── DOM 面板 / DOM Panels (P5-3) ──
  const dmPanel = new DMCreationPanel();
  dmPanel.mount(document.body);
  const narrativePanel = new NarrativePanel();
  narrativePanel.mount(document.body);
  const eventPanel = new EventPanel();
  eventPanel.mount(document.body);
  const characterPanel = new CharacterPanel();
  characterPanel.mount(document.body);
  const objectPanel = new ObjectPanel();
  objectPanel.mount(document.body);
  (window as any).gameStore = gameStore;
  console.log(`${L} DOM panels mounted: dm + narrative + event + character + object`);




  // ── 控制器 / Controller (P5-4: 状态机 + ▶运行 ⏭自动 ⏸停止) ──
  type RunState = "idle" | "connecting" | "running" | "paused";
  let runState: RunState = "idle";

  const bar = document.createElement("div");
  bar.style.cssText = "position:fixed;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:999;align-items:center;";
  document.body.appendChild(bar);

  const tInput = document.createElement("input");
  tInput.value = "3"; tInput.style.cssText = "width:50px;text-align:center;border-radius:4px;border:1px solid #555;background:#222;color:#fff;";

  const btnRunN = makeBtn("跑N个Tick", "#8e44ad");
  const btnStart = makeBtn("▶ 开始", "#2ecc71");
  const btnPause = makeBtn("⏸ 暂停", "#f39c12");
  const btnResume = makeBtn("⏯ 恢复", "#3498db");
  const btnReset = makeBtn("⏹ 重置", "#e74c3c");
  const btnMap  = makeBtn("🗺 地图", "#555");

  const statusEl = document.createElement("span");
  statusEl.style.cssText = "padding:6px 14px;border-radius:4px;background:rgba(0,0,0,0.7);color:#ffd700;font-size:13px;font-weight:bold;min-width:180px;text-align:center;border:1px solid rgba(255,215,0,0.3);";
  const state = gameStore.getState();
  const llmLabel = state.llm_mock ? "LLM:Mock" : "LLM:Real";
  const dataLabel = `Data:${state.data_mode === "mock" ? "Mock" : state.data_mode}`;
  const dbLabel = state.db_name ? `使用DB:${state.db_name}` : (backendReady ? "DB" : "--");
  statusEl.textContent = backendReady
    ? `${llmLabel} | ${dataLabel} | ${dbLabel}`
    : "后端未就绪";

  bar.appendChild(tInput);
  bar.appendChild(btnRunN);
  
  const separator = document.createElement("div");
  separator.style.width = "24px";
  bar.appendChild(separator);

  bar.appendChild(btnStart);
  bar.appendChild(btnPause);
  bar.appendChild(btnResume);
  bar.appendChild(btnReset);
  
  const separator2 = document.createElement("div");
  separator2.style.width = "24px";
  bar.appendChild(separator2);
  
  bar.appendChild(btnMap);
  bar.appendChild(statusEl);

  // 地图切换测试 / Map cycle test
  const { SCENE_MAP } = await import("./constants");
  const sceneOrder = Object.keys(SCENE_MAP);
  let sceneIdx = 0;
  btnMap.onclick = () => {
    sceneIdx = (sceneIdx + 1) % sceneOrder.length;
    const sceneId = sceneOrder[sceneIdx];
    const spawn = SCENE_MAP[sceneId].spawn;
    const st = gameStore.getState();
    // 主角群集中在出生点 3×3 区域 / Cluster PCs in spawn area
    const updated = st.characters.map((ch, i) => ({
      ...ch,
      scene_id: sceneId,
      position_x: spawn.x + (i % 3) - 1,
      position_y: spawn.y + Math.floor(i / 3) - 1,
    }));
    gameStore.setWorldState(st.world_id, st.scenes, updated, st.items, st.scene_objects, {
      llm_mock: st.llm_mock,
      data_mode: st.data_mode,
      db_name: st.db_name,
      mock_dataset: st.mock_dataset,
    });
    console.log(`${L} 🗺 switched to ${sceneId}`);
  };

  function makeBtn(text: string, bg: string): HTMLButtonElement {
    const b = document.createElement("button");
    b.textContent = text;
    b.style.cssText = `padding:4px 12px;border-radius:4px;border:none;background:${bg};color:#fff;cursor:pointer;`;
    return b;
  }

  function updateButtons(): void {
    const idle = runState === "idle";
    const running = runState === "running";
    const paused = runState === "paused";
    const controlsEnabled = backendReady && idle;

    btnRunN.disabled = !controlsEnabled;
    btnRunN.style.opacity = controlsEnabled ? "1" : "0.4";

    btnStart.disabled = !controlsEnabled;
    btnStart.style.display = (idle || running) ? "inline-block" : "none";
    btnStart.style.opacity = controlsEnabled ? "1" : "0.4";

    btnPause.disabled = !running || !backendReady;
    btnPause.style.display = (idle || running) ? "inline-block" : "none";
    btnPause.style.opacity = running && backendReady ? "1" : "0.4";

    btnResume.style.display = paused ? "inline-block" : "none";
    btnResume.disabled = !backendReady;
    btnResume.style.opacity = backendReady ? "1" : "0.4";

    btnReset.disabled = running || !backendReady;
    btnReset.style.opacity = running || !backendReady ? "0.4" : "1";
  }
  updateButtons();

  // ── TickPlayer (HTTP 轮询，替换 WebSocket) ──
  const { TickPlayer } = await import("./net/TickPlayer");
  const player = new TickPlayer(CONFIG.API.base, world.world_id);

  // 同步当前 tick 并加载历史事件 / Sync current tick and load history
  const displayTick = world.display_tick || 0;
  player.setLastTick(displayTick);
  if (displayTick > 0) {
    statusEl.textContent = `已展示到 Tick ${displayTick}`;
    await player.loadHistory(displayTick);
  }

  // 事件 → Store 桥接 / Event → Store bridge
  window.addEventListener("tick-event", ((e: CustomEvent) => {
    const { type, payload } = e.detail;
    if (type === "dm_narrative" && payload.text) {
      gameStore.addNarrative(payload.text as string);
    }
    gameStore.appendEvent({ type, payload } as any);
  }) as EventListener);

  // 历史事件面板 / History event panel
  const { HistoryEventPanel } = await import("./ui/HistoryEventPanel");
  const historyPanel = new HistoryEventPanel(world.world_id);
  historyPanel.mount(document.body);
  window.addEventListener("show-event-history", () => {
    historyPanel.open(gameStore.getState().display_tick);
  });

  // 叙事转发 / Narrative relay to GameScene
  gameStore.subscribe((s) => {
    const gs = game.scene.scenes.find(sc => sc.scene.key === "Game") as import("./scenes/GameScene").GameScene | undefined;
    if (gs?.setNarrative && s.narrative) gs.setNarrative(s.narrative);
  });

  // ── 按钮行为 / Button behaviors ──

  const onTickCallback = (tick: number, events: any[]) => {
    statusEl.textContent = `展示 Tick ${tick} (${events.length} events)`;
    gameStore.setDisplayTick(tick);
    console.log(`${L} display_tick=${tick} events=${events.map(e => e.type).join(',')}`);
  };

  btnRunN.onclick = async () => {
    if (runState !== "idle") return;
    const n = parseInt(tInput.value) || 1;
    console.log(`${L} 跑N个Tick: ticks=${n}`);
    runState = "connecting"; updateButtons();
    try {
      runState = "running"; updateButtons();
      statusEl.textContent = "运行中...";
      const delivered = await player.runTicks(n, onTickCallback);
      statusEl.textContent = `完成: ${delivered} tick`;
    } catch (e) {
      statusEl.textContent = "错误";
      console.error(`${L} run failed:`, e);
    } finally {
      runState = "idle"; updateButtons();
    }
  };

  btnStart.onclick = async () => {
    if (runState !== "idle") return;
    runState = "connecting"; updateButtons();
    try {
      runState = "running"; updateButtons();
      statusEl.textContent = "持续运行中...";
      await player.startLoop(onTickCallback);
    } catch (e) {
      console.error(`${L} start failed:`, e);
      runState = "idle"; updateButtons();
      statusEl.textContent = "错误";
    }
  };

  btnPause.onclick = async () => {
    if (runState !== "running") return;
    try {
      await player.pauseLoop();
      runState = "paused"; updateButtons();
      statusEl.textContent = "已暂停";
    } catch (e) {
      console.error(`${L} pause failed:`, e);
    }
  };

  btnResume.onclick = async () => {
    if (runState !== "paused") return;
    runState = "connecting"; updateButtons();
    try {
      runState = "running"; updateButtons();
      statusEl.textContent = "持续运行中...";
      await player.resumeLoop(onTickCallback);
    } catch (e) {
      console.error(`${L} resume failed:`, e);
      runState = "paused"; updateButtons();
      statusEl.textContent = "错误";
    }
  };

  btnReset.onclick = async () => {
    if (runState === "running") return;
    try {
      await player.reset();
      gameStore.clear();
      gameStore.setDisplayTick(0);
      statusEl.textContent = "已重置";
    } catch (e) {
      console.error(`${L} reset failed:`, e);
      statusEl.textContent = "重置失败";
    } finally {
      runState = "idle";
      updateButtons();
    }
  };


  console.log(`${L} === main() DONE ===`);
}

main();
