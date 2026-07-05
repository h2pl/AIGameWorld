/** 世界配置层 / World Config Store — 启动时写入，之后只读 */
import type { SceneData, CharacterData, ItemData, SceneObjectData, RuntimeConfig } from "../types";
import { tickStore } from "./TickStore";

export interface WorldState {
  world_id: string; // 当前世界 ID / Current world ID
  scenes: SceneData[]; // 场景列表 / Scene list
  characters: CharacterData[]; // 角色数据 / Character data
  items: ItemData[]; // 物品清单 / Item list
  scene_objects: SceneObjectData[]; // 场景物体 / Scene objects like chests/doors
  runtime: RuntimeConfig; // 运行时配置 / Runtime config (mock mode etc.)
}

type Listener = (state: WorldState) => void;

class WorldStore {
  private state: WorldState;
  private listeners: Set<Listener> = new Set();

  constructor() {
    this.state = {
      world_id: "",
      scenes: [],
      characters: [],
      items: [],
      scene_objects: [],
      runtime: { llm_mock: false, data_mode: "real", db_name: "" },
    };
  }

  getState(): Readonly<WorldState> {
    return this.state;
  }

  /** 设置世界数据 / Set world data — called once by main.ts */
  setWorldState(
    world_id: string,
    scenes: SceneData[],
    characters: CharacterData[],
    items: ItemData[],
    scene_objects: SceneObjectData[],
    llm_mock: boolean,
    data_mode: string,
    db_name: string
  ): void {
    this.state.world_id = world_id;
    this.state.scenes = scenes;
    this.state.characters = characters;
    this.state.items = items;
    this.state.scene_objects = scene_objects;
    this.state.runtime = { llm_mock, data_mode, db_name };
    console.log(
      "[WorldStore] set world=%s chars=%d scenes=%d items=%d objs=%d",
      world_id,
      characters.length,
      scenes.length,
      items.length,
      scene_objects.length
    );
    this.notify();
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    for (const l of this.listeners) l(this.state);
  }
}

export const worldStore = new WorldStore();

/** 初始化世界数据并计算角色位置 / Initialize world data and compute character positions */
export function initWorldWithPositions(
  world_id: string,
  scenes: any[],
  characters: any[],
  items: any[],
  scene_objects: any[],
  llm_mock: boolean,
  data_mode: string,
  db_name: string
): void {
  worldStore.setWorldState(
    world_id,
    scenes,
    characters,
    items,
    scene_objects,
    llm_mock,
    data_mode,
    db_name
  );

  const pos: Record<string, { x: number; y: number }> = {};
  const sceneSpawn = new Map(
    scenes.map((s: any) => [s.id, { x: s.spawn_x ?? 0, y: s.spawn_y ?? 0 }])
  );
  const occupied = new Map<string, Set<string>>();
  for (const ch of characters) {
    if (!ch.is_pc || ch.position_x !== 0 || ch.position_y !== 0) {
      pos[ch.id] = { x: ch.position_x, y: ch.position_y };
      continue;
    }
    const sp = sceneSpawn.get(ch.scene_id) || { x: 0, y: 0 };
    const k = `${sp.x},${sp.y}`;
    if (!occupied.has(k)) occupied.set(k, new Set());
    const used = occupied.get(k)!;
    let done = false;
    for (let dy = -1; dy <= 1 && !done; dy++)
      for (let dx = -1; dx <= 1 && !done; dx++) {
        const c = `${sp.x + dx},${sp.y + dy}`;
        if (!used.has(c)) {
          used.add(c);
          pos[ch.id] = { x: sp.x + dx, y: sp.y + dy };
          done = true;
        }
      }
    if (!done) pos[ch.id] = { x: sp.x, y: sp.y };
  }
  tickStore.setInitialPositions(pos);
}
