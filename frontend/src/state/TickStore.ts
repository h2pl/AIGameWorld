/** Tick 运行时层 / Tick Runtime Store — 每个 tick 事件驱动 */
import type { ActionData, EventData } from "../types";

export interface TickState {
  events: EventData[];
  display_tick: number;
  scene_ready: boolean;
  current_scene_id: string;
  current_map_key: string;
  narrative: string;
  dm_plot_brief: string;
  actions: ActionData[];
  errors: string[];
  character_positions: Record<string, { x: number; y: number }>;
}

type Listener = (state: TickState) => void;

class TickStore {
  private state: TickState;
  private listeners: Set<Listener> = new Set();
  private _eventSeq = 0;

  constructor() {
    this.state = {
      events: [],
      display_tick: 0,
      scene_ready: false,
      current_scene_id: "",
      current_map_key: "",
      narrative: "",
      dm_plot_brief: "",
      actions: [],
      errors: [],
      character_positions: {},
    };
  }

  getState(): Readonly<TickState> {
    return this.state;
  }

  /** 追加事件到列表 / Append event */
  appendEvent(ev: { type: string; payload?: Record<string, unknown> }): void {
    this._appendEvents([
      {
        type: ev.type,
        tick: this.state.display_tick,
        description: JSON.stringify(ev.payload || {}).slice(0, 120),
        payload: ev.payload,
        seq: 0,
      } as EventData,
    ]);
    this.notify();
  }

  /** 追加事件到列表，指定 tick / Append event at specific tick */
  appendEventAt(tick: number, ev: { type: string; payload?: Record<string, unknown> }): void {
    this._appendEvents([
      {
        type: ev.type,
        tick,
        description: JSON.stringify(ev.payload || {}).slice(0, 120),
        payload: ev.payload,
        seq: 0,
      } as EventData,
    ]);
    this.notify();
  }

  private _appendEvents(events: EventData[]): void {
    if (!events.length) return;
    const tagged = events.map((ev) => ({ ...ev, seq: ++this._eventSeq }));
    this.state.events = [...this.state.events, ...tagged];
    if (this.state.events.length > 200) {
      this.state.events = this.state.events.slice(-200);
    }
    // 处理 dm_create 事件（scene_setup 由 SceneSetupHandler 处理）
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

      if (ev.type === "dm_create") {
        const brief = String(payload.plot_brief || "");
        if (brief) this.state.dm_plot_brief = brief;
      }
    }
  }

  /** 设置前端展示 tick */
  setDisplayTick(tick: number): void {
    this.state.display_tick = tick;
    this.notify();
  }

  /** 设置场景就绪（scene_setup 消费）/ Set scene ready with metadata */
  setSceneReady(
    sceneId: string,
    mapKey: string,
    positions?: Record<string, { x: number; y: number }>
  ): void {
    this.state.scene_ready = true;
    this.state.current_scene_id = sceneId;
    if (mapKey) this.state.current_map_key = mapKey;
    if (positions) Object.assign(this.state.character_positions, positions);
    console.log("[TickStore] scene_ready → true, scene_id=%s, map_key=%s", sceneId, mapKey);
    this.notify();
  }

  /** 添加叙事 */
  addNarrative(text: string): void {
    this.state.narrative = text;
    this.notify();
  }

  /** 清空运行时数据 */
  clear(): void {
    this.state.display_tick = 0;
    this.state.narrative = "";
    this.state.actions = [];
    this.state.events = [];
    this.state.errors = [];
    this.state.scene_ready = false;
    this.state.current_scene_id = "";
    this.state.current_map_key = "";
    this.state.dm_plot_brief = "";
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

export const tickStore = new TickStore();
