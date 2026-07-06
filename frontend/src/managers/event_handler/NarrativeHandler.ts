// -- file start -- / file start
/** 叙事事件处理器 / Narrative event handler — 等待 NarrativePanel 逐字展示完成 */
import type { EventData } from "../../types";
import { speedMs } from "../../config/playback";

const COMPLETE_TIMEOUT_MS = 8000; // 最长等待逐字完成 / Max wait for typewriter
const READ_DWELL_MS = 600; // 展示完成后额外阅读时间 / Extra reading time after reveal

export class NarrativeHandler {
  /** 处理叙事事件：等待面板逐字展示完成并短暂停留 / Wait for panel reveal and dwell */
  async handle(ev: EventData): Promise<void> {
    const text = ev.payload?.text as string | undefined;
    if (!text) return;

    await this._waitForReveal();
    await new Promise((r) => setTimeout(r, speedMs(READ_DWELL_MS)));
  }

  /** 等待 narrative-complete 事件，带兜底超时 / Wait for narrative-complete with timeout */
  private _waitForReveal(): Promise<void> {
    return new Promise<void>((resolve) => {
      const onComplete = () => {
        window.removeEventListener("narrative-complete", onComplete);
        resolve();
      };
      window.addEventListener("narrative-complete", onComplete);
      setTimeout(() => {
        window.removeEventListener("narrative-complete", onComplete);
        resolve();
      }, COMPLETE_TIMEOUT_MS);
    });
  }
}
