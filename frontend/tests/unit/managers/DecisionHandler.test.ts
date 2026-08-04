// --- 测试 / Tests ---
/** DecisionHandler 单元测试 */
import { describe, it, vi } from "vitest";
import { DecisionHandler } from "../../../src/managers/event_handler/DecisionHandler";

const makeSprite = () => ({
  rawSprite: { id: "sprite" },
  think: vi.fn((text: string, onHide?: () => void) => {
    onHide?.();
  }),
});

describe("DecisionHandler", () => {
  it("should show thought bubble for pc_decision event", async () => {
    const sprite = makeSprite();
    const handler = new DecisionHandler(() => sprite as any, vi.fn());
    await handler.handle({
      type: "pc_decision",
      tick: 1,
      payload: {
        pc_id: "pc-1",
        pc_name: "Alex",
        action_type: "talk",
        target_id: "npc-1",
        target_type: "actor",
        thought: "我想找 NPC 打听消息。",
        reasoning: "先交谈收集情报。",
      },
    });
    expect(sprite.think).toHaveBeenCalled();
  });

  it("should handle missing payload gracefully", async () => {
    const handler = new DecisionHandler(vi.fn(), vi.fn());
    await handler.handle({ type: "pc_decision", tick: 1 });
  });

  it("should handle missing sprite gracefully", async () => {
    const handler = new DecisionHandler(() => undefined, vi.fn());
    await handler.handle({
      type: "pc_decision",
      tick: 1,
      payload: { pc_id: "pc-1" },
    });
  });
});
