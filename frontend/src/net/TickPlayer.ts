/** HTTP TickPlayer — Orchestrator 直接驱动，无后台任务 / Orchestrator-driven, no background tasks.
 *
 * GET /tick/next → orch.run_tick() → { tick, narrative, events[] }
 * 无 ack/pause/resume 概念。
 */

import { gameStore } from "../state/GameStore";

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

  setLastTick(tick: number): void {
    this._lastTick = tick;
  }

  /** 加载历史事件（从 0 到 targetTick）并追加到 store，不播放动画 */
  async loadHistory(targetTick: number): Promise<void> {
    let since = 0;
    while (this._state === "idle" && since < targetTick) {
      try {
        const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/events?since_tick=${since}`);
        if (!resp.ok) break;
        const data = await resp.json() as { events: TickEvent[]; current_tick: number };
        if (data.events && data.events.length > 0) {
          for (const ev of data.events) {
            // 用事件自身的 tick，而不是 current_tick / Use event's own tick
            gameStore.appendEventAt(ev.tick, { type: ev.type, payload: ev.payload });
          }
        }
        since = data.current_tick;
        if (since >= targetTick) break;
        await _sleep(200);
      } catch (e) {
        console.warn(`${L} loadHistory failed`, e);
        break;
      }
    }
    gameStore.setTick(targetTick);
  }

  /** 运行 N 个 tick：通知后端批量生成，前端主动拉取，全部到齐后按顺序展示 */
  async runTicks(n: number, onTick: (tick: number, events: TickEvent[]) => void): Promise<number> {
    if (this._state === "running") return 0;
    this._state = "running";
    const startTick = this._lastTick;
    const targetTick = startTick + n;

    // 1. 通知后端跑 N 个 tick（不等待返回数据）
    try {
      const notify = await fetch(`${this._baseUrl}/api/world/${this._worldId}/tick/batch/${n}`, { method: "POST" });
      if (!notify.ok) {
        throw new Error(`${L} batch/${n} failed: ${notify.status}`);
      }
    } catch (e) {
      this._state = "idle";
      throw e;
    }

    // 2. 主动轮询 /events，直到 N 个 tick 的数据都生成完毕
    let delivered = 0;
    let lastPolledTick = startTick;
    let emptyPolls = 0;
    while (this._state === "running" && lastPolledTick < targetTick) {
      try {
        const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/events?since_tick=${lastPolledTick}`);
        if (!resp.ok) {
          await _sleep(500);
          continue;
        }
        const data = await resp.json() as { events: TickEvent[]; current_tick: number };
        if (data.events && data.events.length > 0) {
          emptyPolls = 0;
          // 按 tick 分组并排序
          const eventsByTick: Record<number, TickEvent[]> = {};
          for (const ev of data.events) {
            // 只接收 startTick < tick <= targetTick 范围内的事件
            if (ev.tick <= startTick || ev.tick > targetTick) continue;
            if (!eventsByTick[ev.tick]) eventsByTick[ev.tick] = [];
            eventsByTick[ev.tick].push(ev);
          }
          const ticks = Object.keys(eventsByTick).map(Number).sort((a, b) => a - b);
          for (const tick of ticks) {
            if (this._state !== "running") break;
            if (tick > targetTick) break;
            this._lastTick = tick;
            lastPolledTick = tick;
            await this._playTick(tick, eventsByTick[tick], onTick);
            delivered++;
          }
        } else {
          emptyPolls++;
          // 连续空轮询 5 次，检查 batch 是否已完成
          if (emptyPolls >= 5) {
            try {
              const statusResp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/status`);
              if (statusResp.ok) {
                const status = await statusResp.json() as { batch_running: boolean };
                if (!status.batch_running) break;
              }
            } catch { /* ignore */ }
          }
        }

        if (lastPolledTick >= targetTick) break;
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
      const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/start`, { method: "POST" });
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
      const resp = await fetch(`${this._baseUrl}/api/world/${this._worldId}/loop/resume`, { method: "POST" });
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
      if (!resp.ok) {
        console.warn(`${L} pull failed with status ${resp.status}`);
        return null;
      }
      return await resp.json() as TickResponse;
    } catch (e) {
      console.warn(`${L} pull failed`, e);
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
