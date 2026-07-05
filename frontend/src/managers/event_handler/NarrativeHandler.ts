// -- file start -- / file start
/** 叙事事件处理器 / Narrative event handler — 直接回调 HUD */
import type { EventData } from "../../types";

export class NarrativeHandler {
  constructor(private onNarrative: (text: string) => void) {}

  handle(ev: EventData): void {
    const text = ev.payload?.text as string | undefined;
    if (text) this.onNarrative(text);
  }
}
