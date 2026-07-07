// --- TickPlayer / Tick Player ---
// --- 状态机 + 轮询 + 事件分发 ---
// --- / ---
// -- file start -- / file start
/** TickPlayer — 控制 tick 播放流程（状态机 + 轮询 + 事件分发） */
import type { EventManager } from "./managers/EventManager";
import type { EventData } from "./types";
import * as API from "./client/api";
import { speedMs } from "./config/playback";
import { createLogger } from "./utils/logger";
import { worldStore } from "./state/WorldStore";
const log = createLogger("TickPlayer");

export type PlayerState = "idle" | "running" | "paused" | "stopped";

export class TickPlayer {
  private _state: PlayerState = "idle";
  private _pending = false;
  private _pollTimer: number | null = null;
  private _lastTick = 0;
  private _baseUrl: string;
  private _worldId: string;
  private _eventManager: EventManager;

  constructor(baseUrl: string, worldId: string, em: EventManager, initialTick: number = 0) {
    this._baseUrl = baseUrl;
    this._worldId = worldId;
    this._eventManager = em;
    this._lastTick = initialTick;
  }

  get state(): PlayerState {
    return this._state;
  }
  get lastTick(): number {
    return this._lastTick;
  }

  /** 从后端恢复当前 tick 的场景 / Recover scene from last tick on page refresh */
  async recoverFromReload(displayTick: number): Promise<void> {
    if (displayTick <= 0) return;
    try {
      const data = await API.fetchEvents(this._baseUrl, this._worldId, displayTick - 1);
      const events = (data.events || []).filter((ev: any) => ev.tick === displayTick);
      if (events.length) {
        const ed: EventData[] = events.map((ev: any) => ({
          type: ev.type,
          tick: ev.tick,
          payload: ev.payload,
        }));
        await this._eventManager.replayTick(displayTick, ed);
        this._lastTick = displayTick;
        log.info(`recovered tick=${displayTick} events=${ed.length}`);
      }
    } catch (e) {
      log.warn(`recoverFromReload failed`, e);
    }
  }

  /** 运行 N 个 tick */
  async runTicks(n: number, onTick: (tick: number, events: any[]) => void): Promise<number> {
    if (this._state === "running" || this._pending) return 0;
    this._pending = true;
    this._state = "running";
    this._eventManager.running = true;
    const targetTick = this._lastTick + n;
    try {
      await API.triggerBatch(this._baseUrl, this._worldId, n);
    } catch (e) {
      this._state = "idle";
      this._pending = false;
      throw e;
    }

    this._emitWaiting(true);
    let delivered = 0;
    while (this._state === "running" && this._lastTick < targetTick) {
      this._emitWaiting(true);
      try {
        const data = await API.fetchEvents(this._baseUrl, this._worldId, this._lastTick);
        if (data.events?.length) {
          const tick = this._lastTick + 1;
          const evs = data.events.filter((ev) => ev.tick === tick);
          if (!evs.length) {
            await _sleep(speedMs(500));
            continue;
          }
          this._lastTick = tick;
          this._emitWaiting(false);
          await this._playTick(tick, evs);
          await API.syncDisplayTick(this._baseUrl, this._worldId, tick);
          onTick(tick, evs);
          delivered++;
        }
      } catch {
        await _sleep(speedMs(500));
      }
      if (this._lastTick >= targetTick) break;
      await _sleep(speedMs(500));
    }
    this._state = "idle";
    this._pending = false;
    this._emitWaiting(false);
    return delivered;
  }

  /** 启动自动循环播放 / Start auto-play loop */
  async startLoop(onTick: (tick: number, events: any[]) => void): Promise<void> {
    if (this._state === "running" || this._pending) return;
    this._pending = true;
    this._state = "running";
    this._eventManager.running = true;
    try {
      await API.startLoop(this._baseUrl, this._worldId);
    } catch (e) {
      this._state = "idle";
      this._pending = false;
      throw e;
    }
    this._pending = false;
    this._startPolling(onTick);
  }

  /** 暂停自动循环 / Pause auto-play loop */
  async pauseLoop(): Promise<void> {
    if (this._state !== "running") return;
    this._state = "paused";
    this._stopPolling();
    this._eventManager.running = false;
    this._emitWaiting(false);
    await API.pauseLoop(this._baseUrl, this._worldId).catch((e) => log.warn(`pause failed`, e));
  }

  async resumeLoop(onTick: (tick: number, events: any[]) => void): Promise<void> {
    if (this._state !== "paused" || this._pending) return;
    this._pending = true;
    this._state = "running";
    this._eventManager.running = true;
    try {
      await API.resumeLoop(this._baseUrl, this._worldId);
    } catch (e) {
      this._state = "paused";
      this._pending = false;
      throw e;
    }
    this._pending = false;
    this._startPolling(onTick);
  }

  /** 重置世界状态 / Reset world state */
  async reset(): Promise<void> {
    this._state = "idle";
    this._stopPolling();
    this._lastTick = 0;
    this._eventManager.running = false;
    this._emitWaiting(false);
    await API.resetWorld(this._baseUrl, this._worldId);
  }

  /** 停止播放 / Stop playback */
  stop(): void {
    this._state = "idle";
    this._stopPolling();
    this._eventManager.running = false;
    this._emitWaiting(false);
  }

  private _startPolling(onTick: (tick: number, events: any[]) => void): void {
    if (this._pollTimer) return;
    const poll = async () => {
      if (this._state !== "running") return;
      this._emitWaiting(true);
      try {
        const data = await API.fetchEvents(this._baseUrl, this._worldId, this._lastTick);
        if (data.events?.length) {
          const tick = this._lastTick + 1;
          const evs = data.events.filter((ev) => ev.tick === tick);
          if (evs.length) {
            this._lastTick = tick;
            this._emitWaiting(false);
            await this._playTick(tick, evs);
            // 播放过程中被暂停则不再同步/回调，避免覆盖“已暂停”状态
            if (this._state !== "running") return;
            await API.syncDisplayTick(this._baseUrl, this._worldId, tick);
            onTick(tick, evs);
          }
        }
      } catch (e) {
        log.warn(`poll failed`, e);
      }
      if (this._state === "running") this._pollTimer = window.setTimeout(poll, speedMs(1000));
    };
    this._pollTimer = window.setTimeout(poll, speedMs(500));
  }

  private _stopPolling(): void {
    if (this._pollTimer) {
      window.clearTimeout(this._pollTimer);
      this._pollTimer = null;
    }
  }

  private _emitWaiting(waiting: boolean, message?: string): void {
    const runtime = worldStore.getState().runtime;
    const isMock = runtime.llm_mock || runtime.data_mode === "mock";
    const defaultMessage = isMock ? "生成 Tick 数据中..." : "等待后端生成 Tick 数据...";
    window.dispatchEvent(
      new CustomEvent("tick-waiting", { detail: { waiting, message: message || defaultMessage } })
    );
  }

  private async _playTick(tick: number, evs: any[]): Promise<void> {
    const ed: EventData[] = evs.map((ev: any) => ({
      type: ev.type,
      tick: ev.tick,
      payload: ev.payload,
    }));
    await this._eventManager.processTick(tick, ed);
  }
}

function _sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
