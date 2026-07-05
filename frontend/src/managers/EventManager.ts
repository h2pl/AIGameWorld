/** 事件管理器 / Event Manager — 统一串行处理一个 tick 内的事件
 *
 * 职责 / Responsibilities:
 *   1. 把一个 tick 的所有事件写入 GameStore（保留历史、供面板展示）
 *   2. 按事件顺序串行调用 handler，前一个事件完成（动画/对话/移动结束）后才处理下一个
 *   3. 未注册 handler 的事件走默认日志处理
 *
 * 用法 / Usage:
 *   const em = new EventManager();
 *   em.register("pc_explore", (ev) => scene.handleExplore(ev));
 *   await em.processTick(tick, events, (t, evs) => { ... });
 */
import { tickStore } from "../state/TickStore";
import type { EventData } from "../types";

/** 事件处理函数 / Event handler function */
export type EventHandlerFn = (ev: EventData) => void | Promise<void>;

export interface EventManagerOptions {
  /** 默认 handler，处理未注册类型 / Default handler for unregistered types */
  defaultHandler?: EventHandlerFn;
}

export class EventManager {
  private handlers: Map<string, EventHandlerFn> = new Map();
  private defaultHandler: EventHandlerFn;

  constructor(options?: EventManagerOptions) {
    this.defaultHandler =
      options?.defaultHandler ||
      ((ev: EventData) => {
        console.log("[EventManager] unhandled event: %s", ev.type);
      });
  }

  /** 注册事件 handler / Register an event handler */
  register(type: string, handler: EventHandlerFn): void {
    this.handlers.set(type, handler);
  }

  /** 取消注册 / Unregister */
  unregister(type: string): void {
    this.handlers.delete(type);
  }

  /** 串行处理一个 tick 的事件 / Process a tick's events sequentially
   *
   * 流程：逐个事件先 dispatch 到事件面板（高亮），再 await handler（动画），
   * 完成后面板去除高亮。
   */
  async processTick(
    tick: number,
    events: EventData[],
    onTick?: (tick: number, events: EventData[]) => void
  ): Promise<void> {
    if (!events.length) return;

    // 1. 写入 store / Persist to store
    for (const ev of events) {
      tickStore.appendEventAt(tick, { type: ev.type, payload: ev.payload });
    }

    // 2. 通知外部（更新 display_tick）/ Notify externals (updates display_tick)
    onTick?.(tick, events);

    // 3. 逐个事件：dispatch → 高亮展示 → await handler → 取消高亮 / Sequential: dispatch → highlight → await handler → unhighlight
    for (const ev of events) {
      window.dispatchEvent(
        new CustomEvent("tick-event", { detail: { type: ev.type, payload: ev.payload } })
      );
      const handler = this.handlers.get(ev.type) || this.defaultHandler;
      const result = handler(ev);
      if (result && typeof result.then === "function") {
        await result;
      }
      window.dispatchEvent(
        new CustomEvent("tick-event", {
          detail: { type: ev.type, payload: ev.payload, phase: "done" },
        })
      );
    }
  }
}
