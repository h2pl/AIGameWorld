// -- file start -- / file start
/** 事件管理器 / Event Manager — 串行 dispatch 事件到 handler 和 window */
import { createLogger } from "../utils/logger";
const log = createLogger("EventManager");
import type { EventData } from "../types";
import { playState } from "../utils/playState";

export type EventHandlerFn = (ev: EventData) => void | Promise<void>;

export class EventManager {
  private handlers: Map<string, EventHandlerFn> = new Map();
  private defaultHandler: EventHandlerFn;

  get running(): boolean { return playState.playing; }
  set running(v: boolean) { playState.playing = v; }

  constructor(opts?: { defaultHandler?: EventHandlerFn }) {
    this.defaultHandler = opts?.defaultHandler || ((ev) => { log.info(`unhandled: ${ev.type}`); });
  }

  register(type: string, handler: EventHandlerFn): void { this.handlers.set(type, handler); }
  unregister(type: string): void { this.handlers.delete(type); }

  /** 正常播放 / Normal playback: dispatch → highlight → await animation → unhighlight */
  async processTick(
    tick: number, events: EventData[], onTick?: (tick: number, events: EventData[]) => void
  ): Promise<void> {
    if (!events.length) return;
    log.info(`tick=${tick} events=${events.length} types=[${events.map(e => e.type).join(",")}]`);

    onTick?.(tick, events);
    window.dispatchEvent(new CustomEvent("tick-start", { detail: { tick } }));

    for (const ev of events) {
      if (!this.running) { log.info(`aborted at tick=${tick}`); break; }
      log.info(`dispatch ${ev.type}`);
      window.dispatchEvent(new CustomEvent("tick-event", { detail: { type: ev.type, payload: ev.payload } }));
      const handler = this.handlers.get(ev.type) || this.defaultHandler;
      const result = handler(ev);
      if (result && typeof result.then === "function") await result;
      window.dispatchEvent(new CustomEvent("tick-event", { detail: { type: ev.type, payload: ev.payload, phase: "done" } }));
    }
  }

  /** 回放模式 / Replay mode: dispatch to panels + handlers, skip animations */
  async replayTick(tick: number, events: EventData[]): Promise<void> {
    if (!events.length) return;
    log.info(`replay tick=${tick} events=${events.length}`);
    window.dispatchEvent(new CustomEvent("tick-start", { detail: { tick } }));

    for (const ev of events) {
      window.dispatchEvent(new CustomEvent("tick-event", { detail: { type: ev.type, payload: ev.payload } }));
      // 只调用 handler（scene_setup → buildScene, dm_create → plot_brief, pc_talk → bubbles）
      const handler = this.handlers.get(ev.type);
      if (handler) {
        const result = handler(ev);
        if (result && typeof result.then === "function") await result;
      }
      window.dispatchEvent(new CustomEvent("tick-event", { detail: { type: ev.type, payload: ev.payload, phase: "done" } }));
    }
  }
}
