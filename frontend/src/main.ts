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
    console.log(`${L} API OK: pack=${data.pack_id} chars=${data.characters?.length || 0}`);
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
  const packId = params.get("pack") || "forgotten_realms";
  console.log(`${L} pack_id=${packId}`);

  // 加载世界数据 / Load world data — 全部依赖后端，失败则提示
  const world = await loadWorldState(packId);
  if (!world) {
    const msg = "❌ 后端未启动。请先运行 aw serve 或 make backend-dev";
    console.error(`${L} ${msg}`);
    document.body.innerHTML = `<div style="color:#ff6b6b;font:16px sans-serif;padding:40px;text-align:center">${msg}</div>`;
    return;
  }
  console.log(`${L} world loaded: ${world.scenes.length} scenes, ${world.characters.length} chars`);
  gameStore.setWorldState(
    world.pack_id,
    world.scenes,
    world.characters,
    world.items,
    world.scene_objects,
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
  const narrativePanel = new NarrativePanel();
  narrativePanel.mount(document.body);
  const eventPanel = new EventPanel();
  eventPanel.mount(document.body);
  const characterPanel = new CharacterPanel();
  characterPanel.mount(document.body);
  const objectPanel = new ObjectPanel();
  objectPanel.mount(document.body);
  console.log(`${L} DOM panels mounted: narrative + event + character + object`);




  // ── 控制器 / Controller (P5-4: 状态机 + ▶运行 ⏭自动 ⏸停止) ──
  type RunState = "idle" | "connecting" | "running";
  let runState: RunState = "idle";
  let autoMode = false;

  const bar = document.createElement("div");
  bar.style.cssText = "position:fixed;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:999;align-items:center;";
  document.body.appendChild(bar);

  const tInput = document.createElement("input");
  tInput.value = "3"; tInput.style.cssText = "width:50px;text-align:center;border-radius:4px;border:1px solid #555;background:#222;color:#fff;";

  const btnRun  = makeBtn("▶ 运行", "#2ecc71");
  const btnAuto = makeBtn("⏭ 自动", "#3498db");
  const btnStop = makeBtn("⏸ 停止", "#e74c3c");
  const btnMap  = makeBtn("🗺 地图", "#8e44ad");

  const statusEl = document.createElement("span");
  statusEl.style.cssText = "padding:6px 14px;border-radius:4px;background:rgba(0,0,0,0.7);color:#ffd700;font-size:13px;font-weight:bold;min-width:140px;text-align:center;border:1px solid rgba(255,215,0,0.3);";
  statusEl.textContent = "就绪";

  bar.appendChild(tInput);
  bar.appendChild(btnRun);
  bar.appendChild(btnAuto);
  bar.appendChild(btnStop);
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
    gameStore.setWorldState(st.pack_id, st.scenes, updated, st.items, st.scene_objects);
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
    btnRun.disabled = !idle;
    btnRun.style.opacity = idle ? "1" : "0.4";
    btnAuto.disabled = !idle && !running;
    btnAuto.style.opacity = (!idle && !running) ? "0.4" : "1";
    btnAuto.textContent = autoMode ? "自动中" : "⏭ 自动";
    btnAuto.style.background = autoMode ? "#f39c12" : "#3498db";
    btnStop.disabled = idle;
    btnStop.style.opacity = idle ? "0.4" : "1";
  }
  updateButtons();

  // ── WebSocket 客户端 / WebSocket Client ──
  const { WSClient } = await import("./net/WSClient");
  const ws = new WSClient("aw");

  // 进度追踪 / Progress tracking
  let totalRequested = 0;
  let lastTick = 0;
  let doneResolve: (() => void) | null = null;
  const progressUnsub = gameStore.subscribe((s) => {
    if (s.current_tick !== lastTick) {
      lastTick = s.current_tick;
      statusEl.textContent = `Running: Tick ${lastTick}/${totalRequested}`;
    }
  });

  // 叙事转发保持 / Narrative relay to GameScene
  gameStore.subscribe((s) => {
    const gs = game.scene.getScene("Game") as import("./scenes/GameScene").GameScene;
    if (gs?.setNarrative && s.narrative) gs.setNarrative(s.narrative);
  });

  // ── 按钮行为 / Button behaviors ──

  /** 执行一次 N tick / Execute N ticks once */
  async function doRun(n: number): Promise<void> {
    totalRequested = n; lastTick = 0;
    statusEl.textContent = `运行中: Tick 0/${n}`;
    ws.runTicks(n);
    await new Promise<void>((resolve) => { doneResolve = resolve; });
  }

  btnRun.onclick = async () => {
    if (runState !== "idle") return;
    const n = parseInt(tInput.value) || 1;
    console.log(`${L} ▶ 运行: ticks=${n}`);
    runState = "connecting"; updateButtons();
    statusEl.textContent = "连接中...";
    try {
      await ws.connect(world.pack_id);
      console.log(`${L} WS connected`);
      runState = "running"; updateButtons();
      await doRun(n);
      statusEl.textContent = `完成: ${lastTick} tick`;
    } catch (e) {
      statusEl.textContent = "错误: 后端未启动";
      console.error(`${L} Run failed:`, e instanceof Error ? e.message : e);
    } finally {
      runState = "idle"; updateButtons();
      doneResolve = null;
    }
  };

  btnAuto.onclick = async () => {
    if (runState === "idle") {
      // 启动自动模式 / Start auto mode
      const n = parseInt(tInput.value) || 1;
      console.log(`${L} ⏭ 自动: ticks=${n}（每批）`);
      autoMode = true;
      runState = "connecting"; updateButtons();
      statusEl.textContent = "连接中...";
      try {
        await ws.connect(world.pack_id);
        console.log(`${L} WS connected（自动）`);
        runState = "running"; updateButtons();
        while (autoMode && runState === "running") {
          await doRun(n);
        }
        autoMode = false; updateButtons();
        statusEl.textContent = `完成: ${lastTick} tick`;
      } catch (e) {
        autoMode = false; updateButtons();
        statusEl.textContent = "错误: 后端未启动";
        console.error(`${L} Auto failed:`, e instanceof Error ? e.message : e);
      } finally {
        runState = "idle"; updateButtons();
        doneResolve = null;
      }
    } else if (runState === "running" && !autoMode) {
      // 运行中切换到自动 / Switch to auto while running
      console.log(`${L} ⏭ 自动: 切换到自动模式`);
      autoMode = true; updateButtons();
      statusEl.textContent = `自动中: Tick ${lastTick}/${totalRequested}`;
    }
  };

  btnStop.onclick = () => {
    console.log(`${L} ⏸ 停止`);
    autoMode = false;
    ws.close();
    if (doneResolve) doneResolve();
    runState = "idle"; updateButtons();
    statusEl.textContent = "已停止";
  };

  // WS done 检测 / Detect completion by watching lastTick >= totalRequested
  const pollDone = setInterval(() => {
    if (runState === "running" && totalRequested > 0 && lastTick >= totalRequested && doneResolve) {
      console.log(`${L} WS done detected: tick=${lastTick}/${totalRequested}`);
      doneResolve(); doneResolve = null;
    }
  }, 300);


  console.log(`${L} === main() DONE ===`);
}

main();
