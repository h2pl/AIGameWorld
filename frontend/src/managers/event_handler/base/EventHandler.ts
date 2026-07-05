/** 事件处理器接口 / Event handler interface
 *
 * 所有 tick 事件处理器都应实现此接口，由 EventManager 串行调度。
 * / All tick event handlers implement this interface and are scheduled by EventManager.
 */
import type { EventData } from "../../../types";

export interface EventHandler {
  handle(ev: EventData): void | Promise<void>;
}
