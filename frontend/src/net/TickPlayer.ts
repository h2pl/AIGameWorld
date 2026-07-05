/** HTTP TickPlayer — 前端按 display_tick 顺序消费事件 / Frontend consumes events by display_tick.
 *
 * 后端生成 data_tick，前端展示 display_tick，展示完一个 tick 后同步到后端。
 * Backend generates data_tick; frontend presents display_tick and syncs progress back.
 */

import { gameStore } from "../state/GameStore";

const L = "[TickPlayer]";

interface TickResponse {
  tick: number;
  tick_message_id: string;
  narrative: string;
  events: TickEvent[];
  data_tick: number;
  display_tick: number;
}

interface TickEvent {
  type: string;
  tick: number;
  payload: Record<string, unknown>;
}

interface EventsResponse {
  events: TickEvent[];
  display_tick: number;
  data_tick: number;
}

export type PlayerState = "idle" | "running" | "stopped";

export class TickPlayer {
  private _state: PlayerState = "idle";
  private _autoMode = false;
  private _pollTimer: number | null = null;
  private _lastTick = 0; // 前端已展示到的 tick / display_tick

  constructor(
    private _baseUrl: string,
    private _worldId: string
  ) {}

  get state(): PlayerState {
    return this._state;
  }

  setLastTick(tick: number): void {
    this._lastTick = tick;
  }

  /** 加载历史事件（从 1 到 targetTick）并追加到 store，不播放动画 */
  async loadHistory(targetTick: number): Promise<void> {
    let since = 0;
    while (this._state === "idle" && since < targetTick) {
      try {
        const resp = await fetch(
          `${this._baseUrl}/api/world/${this._worldId}/events?since_tick=${since}`
        );
        if (!resp.ok) break;
        const data = (await resp.json()) as EventsResponse;
        if (data.events && data.events.length > 0) {
          for (const ev of data.events) {
            gameStore.appendEventAt(ev.tick, { type: ev.type, payload: ev.payload });
          }
          since = data.display_tick;
        } else {
          break;
        }
      } catch (e) {
        console.warn(`${L} loadHistory failed`, e);
        break;
      }
    }
    this._lastTick = targetTick;
    gameStore.setDisplayTick(targetTick);
  }

  /** 运行 N 个 tick：通知后端批量生成，前端按 display_tick 顺序展示 */
  async runTicks(n: number, onTick: (tick: number, events: TickEvent[]) => void): Promise<number> {
    if (this._state === "running") return 0;
    this._state = "running";
    const startTick = this._lastTick;
    const targetTick = startTick + n;

    // 1. 通知后端跑 N 个 tick（不等待返回数据）
    try {
      const notify = await fetch(`${this._baseUrl}/api/world/${this._worldId}/tick/batch/${n}`, {
        method: "POST",
      });
      if (!notify.ok) {
        throw new Error(`${L} batch/${n} failed: ${notify.status}`);
      }
    } catch (e) {
      this._state = "idle";
      throw e;
    }

    // 2. 主动轮询 /events，按 display_tick 顺序展示，展示完一个 tick 同步一次
    let delivered = 0;
    let emptyPolls = 0;
    while (this._state === "running" && this._lastTick < targetTick) {
      try {
        const resp = await fetch(
          `${this._baseUrl}/api/world/${this._worldId}/events?since_tick=${this._lastTick}`
        );
        if (!resp.ok) {
          await _sleep(500);
          continue;
        }
        const data = (await resp.json()) as EventsResponse;
        if (data.events && data.events.length > 0) {
          emptyPolls = 0;
          const tick = this._lastTick + 1;
          // 只应拿到下一个展示 tick 的事件
          const events = data.events.filter((ev) => ev.tick === tick);
          if (events.length === 0) {
            await _sleep(500);
            continue;
          }
          this._lastTick = tick;
          await this._playTick(tick, events, onTick);
          await this._syncDisplayTick(tick);
          delivered++;
        } else {
          emptyPolls++;
          // 连续空轮询 5 次，检查 batch 是否已完成
          if (emptyPolls >= 5) {
            try {
              const statusResp = await fetch(
                `${this._baseUrl}/api/world/${this._worldId}/loop/status`
              );
              if (statusResp.ok) {
                const status = (await statusResp.json()) as { batch_running: boolean };
                if (!status.batch_running) break;
              }
            } catch {
              /* ignore */
            }
          }
        }

        if (this._lastTick >= targetTick) break;
        await _sleep(500);
      } catch (e) {
        console.warn(`${L} runTicks poll failed`, e);
        await _sleep(500);
      }
    }

    this._state = "idle";
    return delivered;
  }

  /** 开始持续循环 (后端驱动) */
  async startLoop(onTick: (tick: number, events: TickEvent[]) => void): Promise<void> {
    if (this._state === "running") return;
    this._state = "running";

    // 通知后端开始
    try {
      const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/start`, {
        method: "POST",
      });
      if (!resp.ok) throw new Error(`${L} loop/start failed: ${resp.status}`);
    } catch (e) {
      this._state = "idle";
      throw e;
    }

    // 开始轮询
    this._startPolling(onTick);
  }

  /** 暂停持续循环 */
  async pauseLoop(): Promise<void> {
    if (this._state !== "running") return;
    this._state = "idle";
    this._stopPolling();

    // 通知后端暂停
    try {
      await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/pause`, { method: "POST" });
    } catch (e) {
      console.warn(`${L} loop/pause failed`, e);
    }
  }

  /** 恢复持续循环 */
  async resumeLoop(onTick: (tick: number, events: TickEvent[]) => void): Promise<void> {
    if (this._state === "running") return;
    this._state = "running";

    // 通知后端恢复
    try {
      const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/resume`, {
        method: "POST",
      });
      if (!resp.ok) throw new Error(`${L} loop/resume failed: ${resp.status}`);
    } catch (e) {
      this._state = "idle";
      throw e;
    }

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
        const resp = await fetch(
          `${this._baseUrl}/api/world/${this._worldId}/events?since_tick=${this._lastTick}`
        );
        const data = (await resp.json()) as EventsResponse;

        if (data.events && data.events.length > 0) {
          const tick = this._lastTick + 1;
          const events = data.events.filter((ev) => ev.tick === tick);
          if (events.length > 0) {
            this._lastTick = tick;
            await this._playTick(tick, events, onTick);
            await this._syncDisplayTick(tick);
          }
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
      if (!resp.ok) {
        console.warn(`${L} pull failed with status ${resp.status}`);
        return null;
      }
      return (await resp.json()) as TickResponse;
    } catch (e) {
      console.warn(`${L} pull failed`, e);
      return null;
    }
  }

  private async _playTick(
    tick: number,
    events: TickEvent[],
    onTick: (tick: number, events: TickEvent[]) => void
  ): Promise<void> {
    // 先把事件写入 store，让 explore/walk-to-talk 等状态被 subscribe 消费
    // / Persist events into store so subscribers (e.g. explore routes) can consume them
    for (const ev of events) {
      gameStore.appendEventAt(ev.tick, { type: ev.type, payload: ev.payload });
    }
    onTick(tick, events);
    for (let i = 0; i < events.length; i++) {
      if (this._state !== "running" && !this._autoMode) break;
      this._emitEvent(events[i].type, events[i].payload);
      if (i < events.length - 1) await _sleep(300);
    }
  }

  /** 同步 display_tick 到后端 / Sync display_tick to backend */
  private async _syncDisplayTick(tick: number): Promise<void> {
    try {
      await fetch(`${this._baseUrl}/api/world/${this._worldId}/tick/display/${tick}`, {
        method: "POST",
      });
    } catch (e) {
      console.warn(`${L} sync display_tick failed`, e);
    }
  }

  private _emitEvent(type: string, payload: Record<string, unknown>): void {
    window.dispatchEvent(new CustomEvent("tick-event", { detail: { type, payload } }));
  }
}

function _sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
