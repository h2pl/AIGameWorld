// --- 测试 / Tests ---
/** NarrativeHandler 单元测试 */
import { afterEach, describe, it, vi } from "vitest";
import { NarrativeHandler } from "../../../src/managers/event_handler/NarrativeHandler";

const REVEAL_TIMEOUT_MS = 8000;
const READ_DWELL_MS = 600;

describe("NarrativeHandler", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("should handle narrative event without error", async () => {
    vi.useFakeTimers();
    const handler = new NarrativeHandler();
    const promise = handler.handle({
      type: "dm_narrative",
      tick: 1,
      payload: { text: "Hello world" },
    });
    // 模拟 NarrativePanel 逐字完成 / Simulate panel typewriter completion
    window.dispatchEvent(
      new CustomEvent("narrative-complete", { detail: { text: "Hello world" } })
    );
    // 让 reveal Promise 解析并调度停留 timer / Let reveal promise resolve and schedule dwell timer
    await Promise.resolve();
    // 推进阅读停留时间 / Advance reading dwell
    vi.advanceTimersByTime(READ_DWELL_MS + 10);
    await promise;
  });

  it("should handle missing payload gracefully", async () => {
    const handler = new NarrativeHandler();
    await handler.handle({ type: "dm_narrative", tick: 1 });
  });

  it("should handle empty text gracefully", async () => {
    const handler = new NarrativeHandler();
    await handler.handle({ type: "dm_narrative", tick: 1, payload: { text: "" } });
  });

  it("should fallback to timeout if complete event never fires", async () => {
    vi.useFakeTimers();
    const handler = new NarrativeHandler();
    const promise = handler.handle({
      type: "dm_narrative",
      tick: 1,
      payload: { text: "Hello world" },
    });
    // 推进 reveal 超时 / Advance reveal timeout
    vi.advanceTimersByTime(REVEAL_TIMEOUT_MS);
    // 让 reveal Promise 解析并调度停留 timer / Let reveal promise resolve and schedule dwell timer
    await Promise.resolve();
    // 推进阅读停留 / Advance reading dwell
    vi.advanceTimersByTime(READ_DWELL_MS + 10);
    await promise;
  });
});
