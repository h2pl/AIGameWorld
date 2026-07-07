/** 叙事事件处理器 / Narrative event handler — 等待 NarrativePanel 展示完成 */
import type { EventData } from "../../types";
import { contentDuration } from "../../utils/contentDuration";

/** 等待 narrative-complete 事件的最大超时 / Max timeout for narrative-complete event */
const COMPLETE_TIMEOUT_MS = 8000;

/** 处理叙事事件：等待面板展示并根据文本长度停留 / Handle narrative event */
export class NarrativeHandler {
  /** 处理单个叙事事件 / Process a single narrative event */
  async handle(ev: EventData): Promise<void> {
    const text = ev.payload?.text as string | undefined;
    if (!text) return;

    // 等待 UI 展示完成 / Wait for UI reveal
    await this._waitForReveal();
    // 根据文本长度停留 / Pause according to text length
    await new Promise((r) => setTimeout(r, contentDuration(text)));
  }

  /** 监听 narrative-complete 事件，超时后自动放行 / Listen for completion with timeout */
  private _waitForReveal(): Promise<void> {
    return new Promise<void>((resolve) => {
      /** 清理监听器并结束等待 / Clean up listener and resolve */
      const onComplete = () => {
        window.removeEventListener("narrative-complete", onComplete);
        resolve();
      };
      window.addEventListener("narrative-complete", onComplete);
      // 兜底超时，避免永久阻塞 / Fallback timeout to avoid blocking forever
      setTimeout(() => {
        window.removeEventListener("narrative-complete", onComplete);
        resolve();
      }, COMPLETE_TIMEOUT_MS);
    });
  }
}
