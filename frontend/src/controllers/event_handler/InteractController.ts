/** 交互事件处理器 / Interact event handler
 *
 * 当前仅作占位：pc_interact 事件尚未在前端实现具体交互表现。
 * / Placeholder for pc_interact events until frontend interaction is implemented.
 */
import type { EventData } from "../../types";
import type { EventController } from "../base/EventController";

export class InteractController implements EventController {
  async handle(ev: EventData): Promise<void> {
    console.log("[InteractController] unhandled interact event:", ev.payload);
  }
}
