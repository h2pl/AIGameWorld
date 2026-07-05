/** GameStore 单元测试 / Unit tests for GameStore
 *
 * 覆盖初始状态、世界状态加载和事件列表追加：
 * / Covers initial state, world state loading, and event list appending
 */
import { describe, it, expect, beforeEach } from "vitest";
import { gameStore } from "../../../src/state/GameStore";
import type { SceneData, CharacterData } from "../../../src/types";

// 测试工厂函数 / Test factory helpers
const makeScene = (id: string, spawnX = 10, spawnY = 10): SceneData => ({
  id,
  name: id,
  type: "village",
  description: `test scene ${id}`,
  spawn_x: spawnX,
  spawn_y: spawnY,
  exits: [],
  landmarks: [],
  environment: {},
});

const makePC = (id: string, sceneId: string, x = 0, y = 0): CharacterData => ({
  id,
  name: id,
  role: "adventurer",
  race: "human",
  status: "active",
  is_pc: true,
  scene_id: sceneId,
  position_x: x,
  position_y: y,
  attributes: {
    strength: 10,
    dexterity: 10,
    constitution: 10,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
  },
  combat: null,
  personality: "brave",
});

describe("GameStore", () => {
  beforeEach(() => {
    // 每个用例前清空 store / Reset store before each test
    gameStore.clear();
  });

  it("should initialize with empty world state", () => {
    const st = gameStore.getState();
    expect(st.world_id).toBe("");
    expect(st.characters).toHaveLength(0);
    expect(st.scene_ready).toBe(false);
  });

  it("should set world state and assign positions to PCs", () => {
    const scene = makeScene("village");
    const pc = makePC("cleric", "village");
    gameStore.setWorldState("mock_world", [scene], [pc], [], [], false, "mock", "dev.db");

    const st = gameStore.getState();
    expect(st.world_id).toBe("mock_world");
    expect(st.runtime.data_mode).toBe("mock");
    // PCs 在 spawn 3x3 区域内偏移 -1 / PCs spawn in a 3x3 area offset by -1
    expect(st.character_positions["cleric"]).toEqual({ x: 9, y: 9 });
    expect(st.scene_ready).toBe(true);
    expect(st.current_scene_id).toBe("village");
  });

  it("should append events and keep them in the events list", () => {
    const scene = makeScene("village");
    const pc = makePC("cleric", "village");
    gameStore.setWorldState("mock_world", [scene], [pc], [], [], false, "mock", "dev.db");

    gameStore.appendEventAt(1, {
      type: "pc_explore",
      payload: {
        pc_id: "cleric",
        waypoints: [{ x: 1, y: 1 }],
        final_x: 3,
        final_y: 3,
      },
    });

    const events = gameStore.getState().events;
    expect(events.length).toBeGreaterThan(0);
    expect(events[events.length - 1].type).toBe("pc_explore");
    expect(events[events.length - 1].tick).toBe(1);
  });
});
