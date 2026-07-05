import { createLogger } from "../../utils/logger";
const log = createLogger("InteractHandler");
/** 交互事件处理器 / Interact event handler
 *
 * 当前仅作占位：pc_interact 事件尚未在前端实现具体交互表现。
 * / Placeholder for pc_interact events until frontend interaction is implemented.
 */
import type { EventData } from "../../types";

export class InteractHandler {
  async handle(ev: EventData): Promise<void> {
    log.info("[InteractHandler] unhandled interact event:", ev.payload);
  }
}
