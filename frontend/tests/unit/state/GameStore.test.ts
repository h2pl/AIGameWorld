// --- 测试 / Tests ---
/** WorldStore 单元测试 / WorldStore unit tests */
import { describe, it, expect } from "vitest";
import { worldStore } from "../../../src/state/WorldStore";

describe("WorldStore", () => {
  it("should initialize with empty state", () => {
    const st = worldStore.getState();
    expect(st.world_id).toBe("");
    expect(st.display_tick).toBe(0);
  });

  it("should set world state", () => {
    worldStore.setWorldState("mock_world", false, "mock", "dev.db");
    const st = worldStore.getState();
    expect(st.world_id).toBe("mock_world");
    expect(st.runtime.data_mode).toBe("mock");
  });

  it("should track display_tick", () => {
    worldStore.setDisplayTick(7);
    expect(worldStore.getState().display_tick).toBe(7);
    worldStore.clear();
    expect(worldStore.getState().display_tick).toBe(0);
  });
});
