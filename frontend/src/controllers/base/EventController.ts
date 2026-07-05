/** 事件控制器接口 / Event controller interface
 *
 * 所有场景级事件控制器都应实现该接口，供 EventManager 串行调度。
 * / All scene-level event controllers implement this for EventManager scheduling.
 */
import type { EventData } from "../../types";

export interface EventController {
  /** 处理单个事件 / Handle a single event */
  handle(ev: EventData): Promise<void>;
  /** 清理状态（可选）/ Clean up state when scene resets */
  clear?(): void;
}
