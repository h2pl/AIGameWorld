// --- 测试 / Tests ---
/** EventManager 单元测试 / EventManager unit tests — register + dispatch + order */
import { describe, it, expect, vi } from "vitest";
import { EventManager } from "../../../src/managers/EventManager";
import type { EventData } from "../../../src/types";

/** 构造测试事件 / Build a test event */
function makeEv(type: string, payload?: Record<string, unknown>): EventData {
  return { type, payload, tick: 1 };
}

describe("EventManager", () => {
  it("should call registered handler for an event", async () => {
    const em = new EventManager();
    const handler = vi.fn();
    em.register("pc_explore", handler);
    await em.processTick(1, [makeEv("pc_explore", { pc_id: "cleric" })]);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({ type: "pc_explore" }));
  });

  it("should process events sequentially and wait for async handlers", async () => {
    const em = new EventManager();
    const order: string[] = [];
    em.register("a", async () => { await new Promise(r => setTimeout(r, 30)); order.push("a"); });
    em.register("b", () => { order.push("b"); });
    await em.processTick(1, [makeEv("a"), makeEv("b")]);
    expect(order).toEqual(["a", "b"]);
  });

  it("should call onTick callback", async () => {
    const em = new EventManager();
    const onTick = vi.fn();
    await em.processTick(2, [makeEv("scene_setup")], onTick);
    expect(onTick).toHaveBeenCalledWith(2, expect.any(Array));
  });

  it("should use default handler for unregistered event types", async () => {
    const defaultHandler = vi.fn();
    const em = new EventManager({ defaultHandler });
    await em.processTick(1, [makeEv("unknown_event")]);
    expect(defaultHandler).toHaveBeenCalledTimes(1);
  });

  it("should abort when running flag is set to false", async () => {
    const em = new EventManager();
    em.running = false;
    const handler = vi.fn();
    em.register("pc_explore", handler);
    await em.processTick(1, [makeEv("pc_explore")]);
    expect(handler).not.toHaveBeenCalled();
  });

  it("should replay events via replayTick without animation delays", async () => {
    const em = new EventManager();
    const handler = vi.fn();
    em.register("scene_setup", handler);
    em.register("pc_talk", handler);
    await em.replayTick(5, [makeEv("scene_setup"), makeEv("pc_talk")]);
    expect(handler).toHaveBeenCalledTimes(2);
  });
});
