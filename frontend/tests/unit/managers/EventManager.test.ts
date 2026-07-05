/** EventManager 单元测试 / Unit tests for EventManager
 *
 * 验证事件按拉取顺序串行处理，前一个完成后再处理下一个。
 * / Verifies events are processed sequentially in fetch order.
 */
import { describe, it, expect, vi } from "vitest";
import { EventManager } from "../../../src/managers/EventManager";
import { gameStore } from "../../../src/state/GameStore";
import type { EventData } from "../../../src/types";

/** 构造测试事件 / Build a test event */
function makeEv(type: string, payload?: Record<string, unknown>): EventData {
  return { type, payload, tick: 1 };
}

describe("EventManager", () => {
  beforeEach(() => {
    // 每个用例前清空 store 事件列表 / Clear store events before each test
    gameStore.clear();
  });

  it("should persist events to store before handling", async () => {
    const em = new EventManager();
    const events = [makeEv("dm_create", { plot_brief: "test" })];

    await em.processTick(1, events);

    const stored = gameStore.getState().events;
    expect(stored.length).toBe(1);
    expect(stored[0].type).toBe("dm_create");
  });

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

    em.register("a", async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
      order.push("a");
    });
    em.register("b", () => {
      order.push("b");
    });

    await em.processTick(1, [makeEv("a"), makeEv("b")]);

    // 即使 a 的 handler 有异步延迟，b 也必须在 a 完成后才执行
    // / Even though a is async, b must run after a completes
    expect(order).toEqual(["a", "b"]);
  });

  it("should call onTick callback after persisting events", async () => {
    const em = new EventManager();
    const onTick = vi.fn();

    await em.processTick(2, [makeEv("scene_setup")], onTick);

    expect(onTick).toHaveBeenCalledWith(2, expect.any(Array));
    // onTick 应该在 store 写入后调用 / onTick should be called after store persistence
    expect(gameStore.getState().events.length).toBe(1);
  });

  it("should use default handler for unregistered event types", async () => {
    const defaultHandler = vi.fn();
    const em = new EventManager({ defaultHandler });

    await em.processTick(1, [makeEv("unknown_event")]);

    expect(defaultHandler).toHaveBeenCalledTimes(1);
  });
});
