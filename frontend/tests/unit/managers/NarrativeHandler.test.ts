// --- 测试 / Tests ---
/** NarrativeHandler 单元测试 */
import { describe, it, expect, vi } from "vitest";
import { NarrativeHandler } from "../../../src/managers/event_handler/NarrativeHandler";

describe("NarrativeHandler", () => {
  it("should call onNarrative when text exists", () => {
    const onNarrative = vi.fn();
    const handler = new NarrativeHandler(onNarrative);
    handler.handle({ type: "dm_narrative", tick: 1, payload: { text: "Hello world" } });
    expect(onNarrative).toHaveBeenCalledWith("Hello world");
  });

  it("should not call onNarrative when payload is missing", () => {
    const onNarrative = vi.fn();
    const handler = new NarrativeHandler(onNarrative);
    handler.handle({ type: "dm_narrative", tick: 1 });
    expect(onNarrative).not.toHaveBeenCalled();
  });

  it("should not call onNarrative when text is empty string", () => {
    const onNarrative = vi.fn();
    const handler = new NarrativeHandler(onNarrative);
    handler.handle({ type: "dm_narrative", tick: 1, payload: { text: "" } });
    expect(onNarrative).not.toHaveBeenCalled();
  });

  it("should handle long narrative text", () => {
    const onNarrative = vi.fn();
    const longText = "A".repeat(1000);
    const handler = new NarrativeHandler(onNarrative);
    handler.handle({ type: "dm_narrative", tick: 1, payload: { text: longText } });
    expect(onNarrative).toHaveBeenCalledWith(longText);
  });
});
