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

  constructor(private _baseUrl: string, private _worldId: string) {}

  get state(): PlayerState { return this._state; }

  /** 运行 N 个 tick，每 tick 回调 onTick(tick, events) */
  async runTicks(n: number, onTick: (tick: number, events: TickEvent[]) => void): Promise<number> {
    let delivered = 0;
    this._state = "running";
    while (delivered < n && this._state === "running") {
      const msg = await this._pullNext();
      if (!msg) break;
      await this._playTick(msg.tick, msg.events, onTick);
      delivered++;
    }
    return delivered;
  }

  /** 自动模式：持续拉取直到 stopped */
  async runAuto(onTick: (tick: number, events: TickEvent[]) => void): Promise<void> {
    this._autoMode = true;
    while (this._autoMode && this._state === "running") {
      const msg = await this._pullNext();
      if (!msg) break;
      await this._playTick(msg.tick, msg.events, onTick);
    }
  }

  stop(): void {
    this._autoMode = false;
    this._state = "idle";
    console.log(`${L} stopped`);
  }

  // ── private ──

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
