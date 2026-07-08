// -- file start -- / file start
/** 事件管理器 / Event Manager — 串行 dispatch + 暂停时中断 */
import { createLogger } from "../utils/logger";
const log = createLogger("EventManager");
import type { EventData } from "../types";
import { playState } from "../utils/playState";

export type EventHandlerFn = (ev: EventData) => void | Promise<void>;

/** 轮询等待暂停信号 / Poll for pause signal */
function _untilPaused(): Promise<void> {
  return new Promise<void>((resolve) => {
    const check = () => (playState.playing ? setTimeout(check, 80) : resolve());
    check();
  });
}

export class EventManager {
  private handlers: Map<string, EventHandlerFn> = new Map();
  private defaultHandler: EventHandlerFn;

  get running(): boolean {
    return playState.playing;
  }
  set running(v: boolean) {
    const was = playState.playing;
    playState.playing = v;
    if (was !== v) {
      window.dispatchEvent(new CustomEvent(v ? "play-resumed" : "play-paused"));
    }
  }

  constructor(opts?: { defaultHandler?: EventHandlerFn }) {
    this.defaultHandler =
      opts?.defaultHandler ||
      ((ev) => {
        log.info(`unhandled: ${ev.type}`);
      });
  }

  register(type: string, handler: EventHandlerFn): void {
    this.handlers.set(type, handler);
  }
  unregister(type: string): void {
    this.handlers.delete(type);
  }

  /** 正常播放 — 可被暂停中断 / Normal playback — interruptible on pause */
  async processTick(
    tick: number,
    events: EventData[],
    onTick?: (tick: number, events: EventData[]) => void
  ): Promise<void> {
    if (!events.length) return;
    log.info(`tick=${tick} events=${events.length} types=[${events.map((e) => e.type).join(",")}]`);

    onTick?.(tick, events);
    window.dispatchEvent(new CustomEvent("tick-start", { detail: { tick } }));

    for (const ev of events) {
      if (!this.running) {
        log.info(`aborted at tick=${tick}`);
        break;
      }
      log.info(`dispatch ${ev.type}`);
      window.dispatchEvent(
        new CustomEvent("tick-event", { detail: { type: ev.type, payload: ev.payload } })
      );
      const handler = this.handlers.get(ev.type) || this.defaultHandler;
      const result = handler(ev);
      if (result && typeof result.then === "function") {
        await Promise.race([result, _untilPaused()]);
      }
      if (!this.running) {
        break;
      }
      window.dispatchEvent(
        new CustomEvent("tick-event", {
          detail: { type: ev.type, payload: ev.payload, phase: "done" },
        })
      );
    }
  }

  /** 回放模式 / Replay mode */
  async replayTick(tick: number, events: EventData[]): Promise<void> {
    if (!events.length) return;
    log.info(`replay tick=${tick} events=${events.length}`);
    window.dispatchEvent(new CustomEvent("tick-start", { detail: { tick } }));

    for (const ev of events) {
      window.dispatchEvent(
        new CustomEvent("tick-event", { detail: { type: ev.type, payload: ev.payload } })
      );
      const handler = this.handlers.get(ev.type);
      if (handler) {
        const result = handler(ev);
        if (result && typeof result.then === "function") await result;
      }
      if (!this.running) {
        break;
      }
      window.dispatchEvent(
        new CustomEvent("tick-event", {
          detail: { type: ev.type, payload: ev.payload, phase: "done" },
        })
      );
    }
  }
}
