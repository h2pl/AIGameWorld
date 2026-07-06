// --- 测试 / Tests ---
/** NarrativeHandler 单元测试 */
import { describe, it } from "vitest";
import { NarrativeHandler } from "../../../src/managers/event_handler/NarrativeHandler";

describe("NarrativeHandler", () => {
  it("should handle narrative event without error", async () => {
    const handler = new NarrativeHandler();
    await handler.handle({ type: "dm_narrative", tick: 1, payload: { text: "Hello world" } });
    // NarrativeHandler now only pauses — text consumed by NarrativePanel via window events
  });

  it("should handle missing payload gracefully", async () => {
    const handler = new NarrativeHandler();
    await handler.handle({ type: "dm_narrative", tick: 1 });
  });

  it("should handle empty text gracefully", async () => {
    const handler = new NarrativeHandler();
    await handler.handle({ type: "dm_narrative", tick: 1, payload: { text: "" } });
  });
});
