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
  world_id: string;
  scenes: SceneData[];
  characters: CharacterData[];
  items: ItemData[];
  scene_objects: SceneObjectData[];
  display_tick: number;
  llm_mock: boolean;
  data_mode: string;
  db_name: string;
  mock_dataset: string;
  scene_ready: boolean; // 是否已收到 scene_setup / Whether scene_setup has been received
  current_scene_id: string; // 当前场景 id / Current scene id
  current_map_key: string; // 当前地图 key / Current map key
  dm_plot_brief: string; // DM 创建情境的 plot_brief / DM creation plot brief
  narrative: string;
  actions: ActionData[];
  events: EventData[];
  errors: string[];
  character_positions: Record<string, { x: number; y: number }>;
  /** 当前待播放的探索路径 / Pending explore waypoints: pc_id → [{x, y}, ...] */
  explore_routes: Record<string, Array<{ x: number; y: number }>>;
  /** 当前待播放的走位对话 / Pending walk-to-talk: {pc_id, target_id, pc_pos, target_pos} */
  walk_to_talk: Array<{
    pc_id: string;
    target_id: string;
    pc_position: { x: number; y: number };
    target_position: { x: number; y: number };
  }>;
}

type Listener = (state: GameState) => void;

class GameStore {
  private state: GameState;
  private listeners: Set<Listener> = new Set();
  private _eventSeq = 0;

  constructor() {
    this.state = {
      world_id: "",
      scenes: [],
      characters: [],
      items: [],
      scene_objects: [],
      display_tick: 0,
      llm_mock: false,
      data_mode: "real",
      db_name: "",
      mock_dataset: "",
      scene_ready: false,
        current_scene_id: "",
        current_map_key: "",
        dm_plot_brief: "",
      narrative: "",
      actions: [],
      events: [],
      errors: [],
      character_positions: {},
      explore_routes: {},
      walk_to_talk: [],
    };
  }

  /** 获取只读状态 / Get read-only state */
  getState(): Readonly<GameState> {
    return this.state;
  }

  /** 设置初始世界状态 / Set initial world state */
  setWorldState(
    world_id: string,
    scenes: SceneData[],
    characters: CharacterData[],
    items: ItemData[],
    scene_objects: SceneObjectData[],
    runtime: { llm_mock: boolean; data_mode: string; db_name: string; mock_dataset: string },
  ): void {
    this.state.world_id = world_id;
    this.state.scenes = scenes;
    this.state.characters = characters;
    this.state.items = items;
    this.state.scene_objects = scene_objects;
    this.state.llm_mock = runtime.llm_mock;
    this.state.data_mode = runtime.data_mode;
    this.state.db_name = runtime.db_name;
    this.state.mock_dataset = runtime.mock_dataset;
    // 按场景 spawn 给未设置坐标的 PC 分配初始位置，避免重叠；NPC 保持固定坐标
    // / Assign initial positions to unset PCs based on scene spawn; keep NPC positions
    const sceneSpawn = new Map(scenes.map((s) => [s.id, { x: s.spawn_x ?? 0, y: s.spawn_y ?? 0 }]));
    const occupied = new Map<string, Set<string>>();
    for (const ch of characters) {
      if (!ch.is_pc || ch.position_x !== 0 || ch.position_y !== 0) {
        this.state.character_positions[ch.id] = { x: ch.position_x, y: ch.position_y };
        continue;
      }
      const spawn = sceneSpawn.get(ch.scene_id) || { x: 0, y: 0 };
      const key = `${spawn.x},${spawn.y}`;
      if (!occupied.has(key)) occupied.set(key, new Set());
      const used = occupied.get(key)!;
      // 3x3 区域顺序占位 / Occupy cells in 3x3 area sequentially
      let assigned = false;
      for (let dy = -1; dy <= 1 && !assigned; dy++) {
        for (let dx = -1; dx <= 1 && !assigned; dx++) {
          const cell = `${spawn.x + dx},${spawn.y + dy}`;
          if (!used.has(cell)) {
            used.add(cell);
            this.state.character_positions[ch.id] = { x: spawn.x + dx, y: spawn.y + dy };
            assigned = true;
          }
        }
      }
      if (!assigned) {
        this.state.character_positions[ch.id] = { x: spawn.x, y: spawn.y };
      }
    }
    console.log(
      "[Store] setWorldState pack=%s chars=%d scenes=%d items=%d objs=%d",
      world_id, characters.length, scenes.length, items.length, scene_objects.length,
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
    // display_tick 由 TickPlayer 按展示进度统一控制，这里不更新
    if (update.type === "dm_narrative" && d.narrative) {
      this.state.narrative = d.narrative;
      this._appendEvents(d.events || []);
    } else if (update.type === "tick_complete") {
      if (d.state_snapshot) {
        const snap = d.state_snapshot;
        this.state.character_positions = snap.character_positions || {};
        Object.entries(this.state.character_positions).forEach(([id, p]) => {
          console.log("[Store]   tick=%d %s → (%d,%d)", d.tick, id, p.x, p.y);
        });
      }
      if (d.actions) this.state.actions = d.actions;
      this._appendEvents(d.events || []);
    } else if (update.type === "phase_update" && d.events) {
      this._appendEvents(d.events);
    }
    if (d.errors?.length) {
      this.state.errors = d.errors;
    }
    this.notify();
  }

  private _appendEvents(events: EventData[]): void {
    if (!events.length) return;
    // 分配单调递增 seq，用于面板去重
    const tagged = events.map((ev) => ({ ...ev, seq: ++this._eventSeq }));
    // 追加而非覆盖，保留历史并限制总容量
    this.state.events = [...this.state.events, ...tagged];
    if (this.state.events.length > 200) {
      this.state.events = this.state.events.slice(-200);
    }
    // 处理 scene_setup / dm_create 事件 / Handle scene setup & DM creation events
    for (const ev of tagged) {
      let payload: Record<string, unknown> | undefined = ev.payload;
      if (!payload && ev.description) {
        try {
          payload = JSON.parse(ev.description) as Record<string, unknown>;
        } catch {
          payload = undefined;
        }
      }
      if (!payload) continue;

      if (ev.type === "scene_setup") {
        const sceneId = String(payload.scene_id || "");
        const scene = payload.scene as Record<string, unknown> | undefined;
        const mapKey = scene ? String(scene.map_key || "") : "";
        if (sceneId) {
          this.state.scene_ready = true;
          this.state.current_scene_id = sceneId;
          if (mapKey) {
            this.state.current_map_key = mapKey;
          }
          console.log("[Store] scene_ready → true, scene_id=%s, map_key=%s", sceneId, mapKey);
        }
        const positions = payload.pc_positions as Record<string, { x: number; y: number }> | undefined;
        if (positions) {
          for (const [id, p] of Object.entries(positions)) {
            this.state.character_positions[id] = p;
          }
          console.log("[Store] scene_setup positions updated", positions);
        }
      }

      if (ev.type === "dm_create") {
        const brief = String(payload.plot_brief || "");
        if (brief) {
          this.state.dm_plot_brief = brief;
          console.log("[Store] dm_plot_brief updated: %s", brief.slice(0, 60));
        }
      }

      // 探索事件：只存路径点，坐标由前端走完动画后回调更新
      // / Explore event: only store waypoints, position updated after animation completes
      if (ev.type === "pc_explore") {
        const pcId = String(payload.pc_id || "");
        const waypoints = payload.waypoints as Array<{ x: number; y: number }> | undefined;
        const finalX = Number(payload.final_x ?? 0);
        const finalY = Number(payload.final_y ?? 0);
        if (pcId && waypoints?.length) {
          this.state.explore_routes = {
            ...this.state.explore_routes,
            [pcId]: [...waypoints, { x: finalX, y: finalY }],
          };
          console.log("[Store] explore route for %s: %d waypoints → final (%d,%d)",
            pcId, waypoints.length, finalX, finalY);
        }
      }

      // 走位对话事件：记录双方坐标供场景动画 / Walk-to-talk: record both positions for scene animation
      if (ev.type === "pc_talk") {
        const pcId = String(payload.pc_id || "");
        const targetId = String(payload.target_id || "");
        const pcPos = payload.pc_position as { x: number; y: number } | undefined;
        const targetPos = payload.target_position as { x: number; y: number } | undefined;
        if (pcId && targetId && pcPos && targetPos) {
          this.state.walk_to_talk = [
            ...this.state.walk_to_talk,
            { pc_id: pcId, target_id: targetId, pc_position: pcPos, target_position: targetPos },
          ];
          console.log("[Store] walk-to-talk: %s→%s (%d,%d)→(%d,%d)",
            pcId, targetId, pcPos.x, pcPos.y, targetPos.x, targetPos.y);
        }
      }
    }
  }

  /** 批量更新角色位置（静默，applyTickUpdate 会统一 notify）/ Batch update positions (silent, notify via applyTickUpdate) */
  updatePositions(pos: Record<string, { x: number; y: number }>): void {
    for (const [id, p] of Object.entries(pos)) {
      this.state.character_positions[id] = p;
    }
    console.log("[Store] updatePositions %d chars: %s", Object.keys(pos).length, Object.keys(pos).join(","));
    // notify() 由 applyTickUpdate 统一触发，避免 sync 双次调用
  }

  /** 设置前端展示 tick */
  setDisplayTick(tick: number): void {
    this.state.display_tick = tick;
    this.notify();
  }

  /** 追加事件到列表 */
  appendEvent(ev: { type: string; payload?: Record<string, unknown> }): void {
    this._appendEvents([{
      type: ev.type,
      tick: this.state.display_tick,
      description: JSON.stringify(ev.payload || {}).slice(0, 120),
      payload: ev.payload,
      seq: 0,
    } as EventData]);
    this.notify();
  }

  /** 追加事件到列表，指定 tick（用于历史加载）/ Append event at specific tick (for history) */
  appendEventAt(tick: number, ev: { type: string; payload?: Record<string, unknown> }): void {
    this._appendEvents([{
      type: ev.type,
      tick,
      description: JSON.stringify(ev.payload || {}).slice(0, 120),
      payload: ev.payload,
      seq: 0,
    } as EventData]);
    this.notify();
  }

  /** 添加叙事 / Add narrative */
  addNarrative(text: string): void {
    this.state.narrative = text;
    this.notify();
  }

  /** 清空运行时数据 / Clear runtime data */
  clear(): void {
    this.state.display_tick = 0;
    this.state.narrative = "";
    this.state.actions = [];
    this.state.events = [];
    this.state.errors = [];
    this.state.explore_routes = {};
    this.state.walk_to_talk = [];
    // 重置场景状态，让 Phaser 重新等待 DM 创造情境 / Reset scene state for fresh DM creation
    this.state.scene_ready = false;
    this.state.current_scene_id = "";
    this.state.current_map_key = "";
    this.state.dm_plot_brief = "";
    this.notify();
  }

  /** 消费并清空探索路径 / Consume and clear explore routes */
  consumeExploreRoutes(): Record<string, Array<{ x: number; y: number }>> {
    const routes = { ...this.state.explore_routes };
    this.state.explore_routes = {};
    return routes;
  }

  /** 消费并清空走位对话 / Consume and clear walk-to-talk list */
  consumeWalkToTalk(): Array<{
    pc_id: string;
    target_id: string;
    pc_position: { x: number; y: number };
    target_position: { x: number; y: number };
  }> {
    const items = [...this.state.walk_to_talk];
    this.state.walk_to_talk = [];
    return items;
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
