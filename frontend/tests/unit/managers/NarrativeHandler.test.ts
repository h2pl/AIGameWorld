// --- 测试 / Tests ---
/** NarrativeHandler 单元测试 */
import { afterEach, describe, it, vi } from "vitest";
import { NarrativeHandler } from "../../../src/managers/event_handler/NarrativeHandler";

const REVEAL_TIMEOUT_MS = 8000;
const READ_DWELL_MIN_MS = 1000;

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
    window.dispatchEvent(
      new CustomEvent("narrative-complete", { detail: { text: "Hello world" } })
    );
    await Promise.resolve();
    // "Hello world" → contentDuration = 1000 + 11*20 = 1220ms
    vi.advanceTimersByTime(2000);
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
    vi.advanceTimersByTime(REVEAL_TIMEOUT_MS);
    await Promise.resolve();
    vi.advanceTimersByTime(2000);
    await promise;
  });
});
