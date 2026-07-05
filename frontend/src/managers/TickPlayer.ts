/** TickPlayer — 控制 tick 播放流程（状态机 + 轮询 + 事件分发），HTTP 调用委托给 api.ts */
import { tickStore } from "../state/TickStore";
import type { EventManager } from "../managers/EventManager";
import type { EventData } from "../types";
import * as API from "../client/api";
import { speedMs } from "../config/playback";

const L = "[TickPlayer]";

export interface TickEvent {
  type: string;
  tick: number;
  payload: Record<string, unknown>;
}

export type PlayerState = "idle" | "running" | "stopped";

export class TickPlayer {
  private _state: PlayerState = "idle";
  private _pollTimer: number | null = null;
  private _lastTick = 0;

  constructor(
    private _baseUrl: string,
    private _worldId: string,
    private _eventManager: EventManager
  ) {}

  get state(): PlayerState {
    return this._state;
  }
  // 设置最后 tick / Set last tick
  setLastTick(tick: number): void {
    this._lastTick = tick;
  }

  /** 加载历史事件到 store（不播放动画）/ Load history into store without animation */
  async loadHistory(targetTick: number): Promise<void> {
    let since = 0;
    while (this._state === "idle" && since < targetTick) {
      try {
        const data = await API.fetchEvents(this._baseUrl, this._worldId, since);
        if (data.events?.length) {
          for (const ev of data.events) {
            tickStore.appendEventAt(ev.tick, { type: ev.type, payload: ev.payload });
          }
          since = data.display_tick;
        } else break;
      } catch (e) {
        console.warn(`${L} loadHistory failed`, e);
        break;
      }
    }
    this._lastTick = targetTick;
    tickStore.setDisplayTick(targetTick);
  }

  /** 运行 N 个 tick：通知后端批量生成 → 轮询消费 / Run N ticks: trigger backend batch → poll results */
  async runTicks(n: number, onTick: (tick: number, events: TickEvent[]) => void): Promise<number> {
    if (this._state === "running") return 0;
    this._state = "running";
    const targetTick = this._lastTick + n;

    try {
      await API.triggerBatch(this._baseUrl, this._worldId, n);
    } catch (e) {
      this._state = "idle";
      throw e;
    }

    let delivered = 0;
    let emptyPolls = 0;
    while (this._state === "running" && this._lastTick < targetTick) {
      try {
        const data = await API.fetchEvents(this._baseUrl, this._worldId, this._lastTick);
        if (data.events?.length) {
          emptyPolls = 0;
          const tick = this._lastTick + 1;
          const events = data.events.filter((ev) => ev.tick === tick);
          if (events.length === 0) {
            await _sleep(speedMs(500));
            continue;
          }
          this._lastTick = tick;
          await this._playTick(tick, events, onTick);
          await API.syncDisplayTick(this._baseUrl, this._worldId, tick);
          delivered++;
        } else {
          emptyPolls++;
          if (emptyPolls >= 5) {
            const status = await API.fetchLoopStatus(this._baseUrl, this._worldId).catch(() => ({
              batch_running: true,
            }));
            if (!status.batch_running) break;
          }
        }
        if (this._lastTick >= targetTick) break;
        await _sleep(speedMs(500));
      } catch (e) {
        console.warn(`${L} runTicks poll failed`, e);
        await _sleep(speedMs(500));
      }
    }
    this._state = "idle";
    return delivered;
  }

  /** 开始持续循环 / Start continuous loop */
  async startLoop(onTick: (tick: number, events: TickEvent[]) => void): Promise<void> {
    if (this._state === "running") return;
    this._state = "running";
    try {
      await API.startLoop(this._baseUrl, this._worldId);
    } catch (e) {
      this._state = "idle";
      throw e;
    }
    this._startPolling(onTick);
  }

  /** 暂停循环 / Pause loop */
  async pauseLoop(): Promise<void> {
    if (this._state !== "running") return;
    this._state = "idle";
    this._stopPolling();
    await API.pauseLoop(this._baseUrl, this._worldId).catch((e) =>
      console.warn(`${L} pause failed`, e)
    );
  }

  /** 恢复循环 / Resume loop */
  async resumeLoop(onTick: (tick: number, events: TickEvent[]) => void): Promise<void> {
    if (this._state === "running") return;
    this._state = "running";
    try {
      await API.resumeLoop(this._baseUrl, this._worldId);
    } catch (e) {
      this._state = "idle";
      throw e;
    }
    this._startPolling(onTick);
  }

  /** 重置 / Reset world */
  async reset(): Promise<void> {
    this._state = "idle";
    this._stopPolling();
    this._lastTick = 0;
    await API.resetWorld(this._baseUrl, this._worldId);
  }

  // 停止 / Stop
  stop(): void {
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
        const data = await API.fetchEvents(this._baseUrl, this._worldId, this._lastTick);
        if (data.events?.length) {
          const tick = this._lastTick + 1;
          const events = data.events.filter((ev) => ev.tick === tick);
          if (events.length > 0) {
            this._lastTick = tick;
            await this._playTick(tick, events, onTick);
            await API.syncDisplayTick(this._baseUrl, this._worldId, tick);
          }
        }
      } catch (e) {
        console.warn(`${L} poll events failed`, e);
      }
      if (this._state === "running") {
        this._pollTimer = window.setTimeout(poll, speedMs(1000));
      }
    };
    this._pollTimer = window.setTimeout(poll, speedMs(500));
  }

  private _stopPolling() {
    if (this._pollTimer) {
      window.clearTimeout(this._pollTimer);
      this._pollTimer = null;
    }
  }

  private async _playTick(
    tick: number,
    events: TickEvent[],
    onTick: (tick: number, events: TickEvent[]) => void
  ): Promise<void> {
    const eventData: EventData[] = events.map((ev) => ({
      type: ev.type,
      tick: ev.tick,
      payload: ev.payload,
    }));
    await this._eventManager.processTick(tick, eventData, (t, evs) =>
      onTick(t, evs as TickEvent[])
    );
  }
}

function _sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
