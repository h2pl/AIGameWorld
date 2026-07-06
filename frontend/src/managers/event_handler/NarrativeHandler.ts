// -- file start -- / file start
/** 叙事事件处理器 / Narrative event handler — 叙事文本由 NarrativePanel 消费，此处仅做停留控制 */
import type { EventData } from "../../types";
import { speedMs } from "../../config/playback";

export class NarrativeHandler {
  /** 处理叙事事件：停留一段时间供阅读 / Handle narrative event, pause for reading */
  async handle(ev: EventData): Promise<void> {
    const text = ev.payload?.text as string | undefined;
    if (!text) return;
    const dwell = Math.min(4000, Math.max(1500, text.length * 80));
    await new Promise((r) => setTimeout(r, speedMs(dwell)));
  }
}
