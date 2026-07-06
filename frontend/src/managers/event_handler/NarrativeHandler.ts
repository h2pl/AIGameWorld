// -- file start -- / file start
/** 叙事事件处理器 / Narrative event handler — show on HUD and pause for reading */
import type { EventData } from "../../types";
import { speedMs } from "../../config/playback";

export class NarrativeHandler {
  constructor(private onNarrative: (text: string) => void) {}

  /** 处理叙事事件：展示并停留一段时间 / Handle narrative event, then pause */
  async handle(ev: EventData): Promise<void> {
    const text = ev.payload?.text as string | undefined;
    if (!text) return;
    this.onNarrative(text);
    // 按文本长度停留，最少 1.5s，最长 4s / Dwell based on length
    const dwell = Math.min(4000, Math.max(1500, text.length * 80));
    await new Promise((r) => setTimeout(r, speedMs(dwell)));
  }
}
