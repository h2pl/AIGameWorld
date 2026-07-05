/** 叙事事件处理器 / Narrative event handler */
import { tickStore } from "../../state/TickStore";
import type { EventData } from "../../types";

export class NarrativeHandler {
  async handle(ev: EventData): Promise<void> {
    const text = ev.payload?.text as string | undefined;
    if (text) {
      // 统一更新 store，由 subscribe 同步 narrativeText 和 narrative 面板
      // / Update store uniformly; subscribe syncs narrativeText and narrative panel
      tickStore.addNarrative(text);
    }
  }
}
