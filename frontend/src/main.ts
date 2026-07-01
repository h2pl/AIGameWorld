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

/** Mock 数据 / Mock data — 后端不可用时的回退 */
function loadMockState(): InitialWorldState {
  return {
    pack_id: "forgotten_realms",
    scenes: [{
      id: "village_elderwood",
      name: "Elderwood Village",
      type: "village",
      description: "A quiet border village, smoke rising from the blacksmith's chimney.",
      exits: [{
        target_scene: "forest_north",
        position: { x: 28, y: 0 },
        description: "Path to the northern forest",
      }],
      landmarks: [
        { id: "blacksmith_shop", name: "铁匠铺", position: { x: 5, y: 7 } },
        { id: "tavern", name: "酒馆", position: { x: 15, y: 3 } },
        { id: "market", name: "集市", position: { x: 12, y: 10 } },
      ],
      environment: { weather: "clear", time_of_day: "morning" },
    }],
    characters: [
      {
        id: "pc_fighter", name: "Kael", role: "fighter", race: "human",
        status: "active", scene_id: "village_elderwood",
        position_x: 6, position_y: 6,
        attributes: { strength: 16, dexterity: 12, constitution: 14, intelligence: 10, wisdom: 10, charisma: 12 },
        combat: { hp: 28, max_hp: 28, ac: 16, attack_bonus: 5, damage_dice: "1d8", initiative: 2 },
        personality: "Brave but impulsive.", character_arc: { stage: "growth", description: "Prove himself" },
        is_pc: true,
      },
      {
        id: "pc_rogue", name: "Zeph", role: "rogue", race: "elf",
        status: "active", scene_id: "village_elderwood",
        position_x: 14, position_y: 6,
        attributes: { strength: 10, dexterity: 18, constitution: 12, intelligence: 14, wisdom: 12, charisma: 14 },
        combat: { hp: 20, max_hp: 20, ac: 14, attack_bonus: 6, damage_dice: "1d6", initiative: 4 },
        personality: "Sly and curious.", character_arc: { stage: "crisis", description: "Trust issues" },
        is_pc: true,
      },
      {
        id: "pc_cleric", name: "Elara", role: "cleric", race: "human",
        status: "active", scene_id: "village_elderwood",
        position_x: 6, position_y: 12,
        attributes: { strength: 12, dexterity: 10, constitution: 14, intelligence: 12, wisdom: 18, charisma: 14 },
        combat: { hp: 24, max_hp: 24, ac: 18, attack_bonus: 4, damage_dice: "1d8", initiative: 1 },
        personality: "Calm and devout.", character_arc: { stage: "growth", description: "Seeking signs" },
        is_pc: true,
      },
      {
        id: "pc_wizard", name: "Mira", role: "wizard", race: "elf",
        status: "active", scene_id: "village_elderwood",
        position_x: 14, position_y: 12,
        attributes: { strength: 8, dexterity: 14, constitution: 12, intelligence: 18, wisdom: 14, charisma: 10 },
        combat: { hp: 16, max_hp: 16, ac: 12, attack_bonus: 3, damage_dice: "1d6", initiative: 2 },
        personality: "Brilliant but aloof.", character_arc: { stage: "setup", description: "Uncover ancient lore" },
        is_pc: true,
      },
      {
        id: "actor_blacksmith", name: "Garret", role: "blacksmith", race: "dwarf",
        status: "active", scene_id: "village_elderwood",
        position_x: 4, position_y: 8,
        attributes: { strength: 14, dexterity: 10, constitution: 16, intelligence: 12, wisdom: 10, charisma: 10 },
        combat: null,
        personality: "Gruff but kind.", functions: ["merchant"],
        is_pc: false,
      },
      {
        id: "actor_guard", name: "Borin", role: "guard", race: "human",
        status: "active", scene_id: "village_elderwood",
        position_x: 10, position_y: 2,
        attributes: { strength: 14, dexterity: 10, constitution: 14, intelligence: 10, wisdom: 12, charisma: 10 },
        combat: { hp: 22, max_hp: 22, ac: 15, attack_bonus: 4, damage_dice: "1d8", initiative: 1 },
        personality: "Stern but fair.", functions: ["guard"],
        is_pc: false,
      },
      {
        id: "actor_merchant", name: "Selia", role: "merchant", race: "human",
        status: "active", scene_id: "village_elderwood",
        position_x: 24, position_y: 8,
        attributes: { strength: 8, dexterity: 12, constitution: 10, intelligence: 14, wisdom: 12, charisma: 16 },
        combat: null,
        personality: "Charming and shrewd.", functions: ["merchant"],
        is_pc: false,
      },
    ],
    items: [
      { id: "longsword", name: "Longsword", item_type: "weapon", rarity: "common", description: "A well-forged blade." },
      { id: "health_potion", name: "Health Potion", item_type: "potion", rarity: "common", description: "Heals 2d4+2 HP." },
    ],
    scene_objects: [
      { id: "chest_wooden", name: "Wooden Chest", object_type: "container", scene_id: "village_elderwood", position_x: 20, position_y: 15 },
      { id: "door_cellar", name: "Cellar Door", object_type: "door", scene_id: "village_elderwood", position_x: 25, position_y: 5 },
    ],
  };
}

/** 主入口 / Main entry */
async function main(): Promise<void> {
  console.log(`${L} === main() START ===`);
  const params = new URLSearchParams(window.location.search);
  const packId = params.get("pack") || "forgotten_realms";
  console.log(`${L} pack_id=${packId}`);

  // 加载世界数据 / Load world data
  let world = (await loadWorldState(packId)) || loadMockState();
  // API 可能返回位置全为 (0,0) 的无初始化数据，此时用 mock 兜底
  if (world.characters.length > 0 && world.characters.every(c => !c.position_x && !c.position_y)) {
    console.log(`${L} API positions empty, using mock data`);
    world = loadMockState();
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

  // ── 控制面板 / Control Panel ──
  const bar = document.createElement("div");
  bar.style.cssText = "position:fixed;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:999;";
  document.body.appendChild(bar);

  const tInput = document.createElement("input");
  tInput.value = "3"; tInput.style.cssText = "width:50px;text-align:center;border-radius:4px;border:1px solid #555;background:#222;color:#fff;";

  const btnRun = document.createElement("button");
  btnRun.textContent = "▶ Run";
  btnRun.style.cssText = "padding:4px 12px;border-radius:4px;border:none;background:#2ecc71;color:#fff;cursor:pointer;";

  const status = document.createElement("span");
  status.style.cssText = "color:#aaa;font-size:11px;";
  status.textContent = "Disconnected";

  bar.appendChild(tInput);
  bar.appendChild(btnRun);
  bar.appendChild(status);

  // ── WebSocket 客户端 / WebSocket Client ──
  const { WSClient } = await import("./net/WSClient");
  const ws = new WSClient("aw");

  // 只注册一次叙事监听 / Register narrative listener once
  let narrativeUnsub: (() => void) | null = null;
  gameStore.subscribe((s) => {
    const gs = game.scene.getScene("Game") as import("./scenes/GameScene").GameScene;
    if (gs?.setNarrative && s.narrative) gs.setNarrative(s.narrative);
  });

  btnRun.onclick = async () => {
    const n = parseInt(tInput.value) || 1;
    console.log(`${L} ▶ Run clicked: ticks=${n}`);
    try {
      status.textContent = "Connecting...";
      await ws.connect(world.pack_id);
      console.log(`${L} WS connected, sending run ${n} ticks`);
      status.textContent = "Connected";
      ws.runTicks(n);
      status.textContent = `Running ${n} tick(s)...`;
      await new Promise(r => setTimeout(r, n * 1000 + 500));
      status.textContent = `Connected (tick: ${gameStore.getState().current_tick})`;
      console.log(`${L} Run complete: tick=${gameStore.getState().current_tick}`);
    } catch (e) {
      status.textContent = "Error: backend not running";
      console.error(`${L} Run failed:`, e instanceof Error ? e.message : e);
    }
  };
  console.log(`${L} === main() DONE ===`);
}

main();
