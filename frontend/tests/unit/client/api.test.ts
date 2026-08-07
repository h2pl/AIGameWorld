// --- 测试 / Tests ---
/** API 客户端单元测试 / API client unit tests — fetch + create world + tick operations */
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as API from "../../../src/client/api";

// 覆盖 fetch/create world/tick 拉取 / Covers fetch, world creation, tick fetching
describe("API client", () => {
  const BASE = "http://test";
  const WORLD = "mock_world";

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("should fetch events with correct URL", async () => {
    const mock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      headers: new Headers({ "X-Trace-Id": "test-trace" }),
      json: async () => ({ events: [], display_tick: 0, data_tick: 0 }),
    } as Response);

    await API.fetchEvents(BASE, WORLD, 5);
    expect(mock).toHaveBeenCalledWith(
      `${BASE}/api/world/${WORLD}/events?since_tick=5&tick_limit=1`,
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("should throw on non-ok fetchEvents response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Headers(),
    } as Response);
    await expect(API.fetchEvents(BASE, WORLD, 0)).rejects.toThrow("events 500");
  });

  it("should trigger batch with correct URL", async () => {
    const mock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      headers: new Headers(),
    } as Response);
    await API.triggerBatch(BASE, WORLD, 3);
    expect(mock).toHaveBeenCalledWith(
      `${BASE}/api/world/${WORLD}/tick/batch/3`,
      expect.objectContaining({ method: "POST", headers: expect.any(Object) })
    );
  });

  it("should reset world", async () => {
    const mock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      headers: new Headers(),
    } as Response);
    await API.resetWorld(BASE, WORLD);
    expect(mock).toHaveBeenCalledWith(
      `${BASE}/api/world/${WORLD}/reset`,
      expect.objectContaining({ method: "POST", headers: expect.any(Object) })
    );
  });

  it("should sync display tick", async () => {
    const mock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      headers: new Headers(),
    } as Response);
    await API.syncDisplayTick(BASE, WORLD, 10);
    expect(mock).toHaveBeenCalledWith(
      `${BASE}/api/world/${WORLD}/tick/display/10`,
      expect.objectContaining({ method: "POST", headers: expect.any(Object) })
    );
  });
});
