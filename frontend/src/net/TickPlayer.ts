/** HTTP TickPlayer — Orchestrator 直接驱动，无后台任务 / Orchestrator-driven, no background tasks.
 *
 * GET /tick/next → orch.run_tick() → { tick, narrative, events[] }
 * 无 ack/pause/resume 概念。
 */

const L = "[TickPlayer]";

interface TickResponse {
  tick: number;
  tick_message_id: string;
  narrative: string;
  events: TickEvent[];
}

interface TickEvent {
  type: string;
  tick: number;
  payload: Record<string, unknown>;
}

export type PlayerState = "idle" | "running" | "stopped";

export class TickPlayer {
  private _state: PlayerState = "idle";
  private _autoMode = false;
  private _pollTimer: number | null = null;
  private _lastTick = 0;

  constructor(private _baseUrl: string, private _worldId: string) {}

  get state(): PlayerState { return this._state; }

  /** 运行 N 个 tick，每 tick 回调 onTick(tick, events) */
  async runTicks(n: number, onTick: (tick: number, events: TickEvent[]) => void): Promise<number> {
    let delivered = 0;
    this._state = "running";
    while (delivered < n && this._state === "running") {
      const msg = await this._pullNext();
      if (!msg) break;
      this._lastTick = msg.tick;
      await this._playTick(msg.tick, msg.events, onTick);
      delivered++;
    }
    this._state = "idle";
    return delivered;
  }

  /** 开始持续循环 (后端驱动) */
  async startLoop(onTick: (tick: number, events: TickEvent[]) => void): Promise<void> {
    if (this._state === "running") return;
    this._state = "running";
    
    // 通知后端开始
    await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/start`, { method: "POST" });
    
    // 开始轮询
    this._startPolling(onTick);
  }

  /** 暂停持续循环 */
  async pauseLoop(): Promise<void> {
    if (this._state !== "running") return;
    this._state = "idle";
    this._stopPolling();
    
    // 通知后端暂停
    await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/pause`, { method: "POST" });
  }

  /** 恢复持续循环 */
  async resumeLoop(onTick: (tick: number, events: TickEvent[]) => void): Promise<void> {
    if (this._state === "running") return;
    this._state = "running";
    
    // 通知后端恢复
    await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/resume`, { method: "POST" });
    
    // 开始轮询
    this._startPolling(onTick);
  }

  /** 重置 */
  async reset(): Promise<void> {
    this._state = "idle";
    this._stopPolling();
    this._lastTick = 0;
    await fetch(`${this._baseUrl}/api/world/${this._worldId}/reset`, { method: "POST" });
  }

  stop(): void {
    this._autoMode = false;
    this._state = "idle";
    this._stopPolling();
    console.log(`${L} stopped`);
  }

  // ── private ──

  private _startPolling(onTick: (tick: number, events: TickEvent[]) => void) {
    if (this._pollTimer) return;
    
    const poll = async () => {
      if (this._state !== "running") return;
      
      try {
        const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/events?since_tick=${this._lastTick}`);
        const data = await resp.json();
        
        if (data.events && data.events.length > 0) {
          // 按 tick 分组事件
          const eventsByTick: Record<number, TickEvent[]> = {};
          for (const ev of data.events) {
            if (!eventsByTick[ev.tick]) eventsByTick[ev.tick] = [];
            eventsByTick[ev.tick].push(ev);
          }
          
          const ticks = Object.keys(eventsByTick).map(Number).sort((a, b) => a - b);
          for (const tick of ticks) {
            if (this._state !== "running") break;
            this._lastTick = tick;
            await this._playTick(tick, eventsByTick[tick], onTick);
          }
        } else if (data.current_tick > this._lastTick) {
           this._lastTick = data.current_tick;
        }
      } catch (e) {
        console.warn(`${L} poll events failed`, e);
      }
      
      if (this._state === "running") {
        this._pollTimer = window.setTimeout(poll, 1000);
      }
    };
    
    this._pollTimer = window.setTimeout(poll, 500);
  }

  private _stopPolling() {
    if (this._pollTimer) {
      window.clearTimeout(this._pollTimer);
      this._pollTimer = null;
    }
  }

  private async _pullNext(): Promise<TickResponse | null> {
    try {
      const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/tick/next`);
      return await resp.json() as TickResponse;
    } catch {
      console.warn(`${L} pull failed`);
      return null;
    }
  }

  private async _playTick(
    tick: number, events: TickEvent[],
    onTick: (tick: number, events: TickEvent[]) => void,
  ): Promise<void> {
    onTick(tick, events);
    for (let i = 0; i < events.length; i++) {
      if (this._state !== "running" && !this._autoMode) break;
      this._emitEvent(events[i].type, events[i].payload);
      if (i < events.length - 1) await _sleep(300);
    }
  }

  private _emitEvent(type: string, payload: Record<string, unknown>): void {
    window.dispatchEvent(new CustomEvent("tick-event", { detail: { type, payload } }));
  }
}

function _sleep(ms: number): Promise<void> {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}
