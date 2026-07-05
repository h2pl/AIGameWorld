/** WorldStore + TickStore 单元测试 / Unit tests for WorldStore + TickStore */
import { describe, it, expect, beforeEach } from "vitest";
import { worldStore } from "../../../src/state/WorldStore";
import { tickStore } from "../../../src/state/TickStore";
import type { SceneData, CharacterData } from "../../../src/types";

/** 创建测试场景 / Create test scene */
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

describe("WorldStore", () => {
  it("should initialize with empty state", () => {
    // 初始状态为空 / Initial state is empty
    const st = worldStore.getState();
    expect(st.world_id).toBe("");
    expect(st.characters).toHaveLength(0);
  });

  it("should set world state", () => {
    // 设置世界状态 / Set world state
    const scene = makeScene("village");
    const pc = makePC("cleric", "village");
    worldStore.setWorldState("mock_world", [scene], [pc], [], [], false, "mock", "dev.db");

    const st = worldStore.getState();
    expect(st.world_id).toBe("mock_world");
    expect(st.runtime.data_mode).toBe("mock");
  });
});

describe("TickStore", () => {
  // 每用例前清空 / Reset before each test
  beforeEach(() => tickStore.clear());

  it("should initialize with empty state", () => {
    const st = tickStore.getState();
    expect(st.scene_ready).toBe(false);
    expect(st.events).toHaveLength(0);
  });

  it("should append events", () => {
    tickStore.appendEventAt(1, { type: "scene_setup", payload: { scene_id: "village" } });
    expect(tickStore.getState().events.length).toBe(1);
  });

  it("should set scene_ready via setSceneReady", () => {
    tickStore.setSceneReady("village", "tuxemon-map", { cleric: { x: 9, y: 9 } });

    const st = tickStore.getState();
    expect(st.scene_ready).toBe(true);
    expect(st.current_scene_id).toBe("village");
    expect(st.current_map_key).toBe("tuxemon-map");
    expect(st.character_positions["cleric"]).toEqual({ x: 9, y: 9 });
  });

  it("should set display_tick", () => {
    tickStore.setDisplayTick(5);
    expect(tickStore.getState().display_tick).toBe(5);
  });

  it("should add narrative", () => {
    tickStore.addNarrative("test narrative");
    expect(tickStore.getState().narrative).toBe("test narrative");
  });

  it("should clear runtime state", () => {
    tickStore.appendEventAt(1, { type: "pc_explore" });
    tickStore.clear();
    const st = tickStore.getState();
    expect(st.events).toHaveLength(0);
    expect(st.scene_ready).toBe(false);
    expect(st.display_tick).toBe(0);
  });
});
