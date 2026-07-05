/** 叙事事件控制器 / Narrative event controller */
import { gameStore } from "../state/GameStore";
import type { EventData } from "../types";
import type { EventController } from "./base/EventController";

export class NarrativeController implements EventController {
  async handle(ev: EventData): Promise<void> {
    const text = ev.payload?.text as string | undefined;
    if (text) {
      // 统一更新 store，由 subscribe 同步 narrativeText 和 narrative 面板
      // / Update store uniformly; subscribe syncs narrativeText and narrative panel
      gameStore.addNarrative(text);
    }
  }
}
