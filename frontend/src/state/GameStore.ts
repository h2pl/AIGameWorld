/** 前端状态管理 / Frontend State Store — 简单的发布-订阅模式 */

import type {
  SceneData,
  CharacterData,
  ItemData,
  SceneObjectData,
  TickUpdate,
  ActionData,
  EventData,
} from "../types";

export interface GameState {
  pack_id: string;
  scenes: SceneData[];
  characters: CharacterData[];
  items: ItemData[];
  scene_objects: SceneObjectData[];
  current_tick: number;
  narrative: string;
  actions: ActionData[];
  events: EventData[];
  errors: string[];
  character_positions: Record<string, { x: number; y: number }>;
}

type Listener = (state: GameState) => void;

class GameStore {
  private state: GameState;
  private listeners: Set<Listener> = new Set();

  constructor() {
    this.state = {
      pack_id: "",
      scenes: [],
      characters: [],
      items: [],
      scene_objects: [],
      current_tick: 0,
      narrative: "",
      actions: [],
      events: [],
      errors: [],
      character_positions: {},
    };
  }

  /** 获取只读状态 / Get read-only state */
  getState(): Readonly<GameState> {
    return this.state;
  }

  /** 设置初始世界状态 / Set initial world state */
  setWorldState(
    pack_id: string,
    scenes: SceneData[],
    characters: CharacterData[],
    items: ItemData[],
    scene_objects: SceneObjectData[],
  ): void {
    this.state.pack_id = pack_id;
    this.state.scenes = scenes;
    this.state.characters = characters;
    this.state.items = items;
    this.state.scene_objects = scene_objects;
    // 初始化角色位置 / Init character positions
    for (const ch of characters) {
      this.state.character_positions[ch.id] = { x: ch.position_x, y: ch.position_y };
    }
    console.log(
      "[Store] setWorldState pack=%s chars=%d scenes=%d items=%d objs=%d",
      pack_id, characters.length, scenes.length, items.length, scene_objects.length,
    );
    for (const ch of characters) {
      const p = this.state.character_positions[ch.id];
      console.log("[Store]   %s (%s) pos=(%d,%d) pc=%s", ch.id, ch.name, p.x, p.y, ch.is_pc);
    }
    this.notify();
  }

  /** 应用 tick 更新 / Apply tick update */
  applyTickUpdate(update: TickUpdate): void {
    const d = update.data;
    console.log("[Store] applyTickUpdate type=%s tick=%d", update.type, d.tick);
    if (d.tick) {
      this.state.current_tick = d.tick;
    }
    if (update.type === "dm_narrative" && d.narrative) {
      this.state.narrative = d.narrative;
      this.state.events = d.events || [];
    } else if (update.type === "tick_complete") {
      if (d.state_snapshot) {
        const snap = d.state_snapshot;
        this.state.character_positions = snap.character_positions || {};
        Object.entries(this.state.character_positions).forEach(([id, p]) => {
          console.log("[Store]   tick=%d %s → (%d,%d)", d.tick, id, p.x, p.y);
        });
      }
      if (d.actions) this.state.actions = d.actions;
      if (d.events) this.state.events = d.events;
    } else if (update.type === "phase_update" && d.events) {
      this.state.events = d.events;
    }
    if (d.errors?.length) {
      this.state.errors = d.errors;
    }
    this.notify();
  }

  /** 批量更新角色位置（静默，applyTickUpdate 会统一 notify）/ Batch update positions (silent, notify via applyTickUpdate) */
  updatePositions(pos: Record<string, { x: number; y: number }>): void {
    for (const [id, p] of Object.entries(pos)) {
      this.state.character_positions[id] = p;
    }
    console.log("[Store] updatePositions %d chars: %s", Object.keys(pos).length, Object.keys(pos).join(","));
    // notify() 由 applyTickUpdate 统一触发，避免 sync 双次调用
  }

  /** 添加叙事 / Add narrative */
  addNarrative(text: string): void {
    this.state.narrative = text;
    this.notify();
  }

  /** 清空运行时数据 / Clear runtime data */
  clear(): void {
    this.state.current_tick = 0;
    this.state.narrative = "";
    this.state.actions = [];
    this.state.events = [];
    this.state.errors = [];
    this.notify();
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    for (const l of this.listeners) {
      l(this.state);
    }
  }
}

/** 全局单例 / Global singleton */
export const gameStore = new GameStore();
