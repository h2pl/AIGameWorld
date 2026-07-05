// --- 测试 / Tests ---
/** SceneSetupHandler 单元测试 / SceneSetupHandler unit tests */
import { describe, it, expect, vi } from "vitest";
import { SceneSetupHandler } from "../../../src/managers/event_handler/SceneSetupHandler";
import type { EventData } from "../../../src/types";

describe("SceneSetupHandler", () => {
  function makeEv(payload: Record<string, unknown>): EventData {
    return { type: "scene_setup", tick: 1, payload };
  }

  it("should skip if no payload", () => {
    const fn = vi.fn();
    new SceneSetupHandler(fn).handle({ type: "scene_setup", tick: 1 });
    expect(fn).not.toHaveBeenCalled();
  });

  it("should skip if no scene_id", () => {
    const fn = vi.fn();
    new SceneSetupHandler(fn).handle(makeEv({ scene_id: "" }));
    expect(fn).not.toHaveBeenCalled();
  });

  it("should pass SceneSetupData object", () => {
    const fn = vi.fn();
    new SceneSetupHandler(fn).handle(makeEv({
      scene_id: "desert",
      scene: { map_key: "desert-map", name: "Desert", ext_json: "" },
      pcs: [{ id: "c", position_x: 5, position_y: 5 }],
      actors: [{ id: "a", position_x: 8, position_y: 8 }],
    }));
    expect(fn).toHaveBeenCalledWith(expect.objectContaining({
      sceneId: "desert", mapKey: "desert-map", sceneName: "Desert",
      pcs: [{ id: "c", position_x: 5, position_y: 5 }],
      actors: [{ id: "a", position_x: 8, position_y: 8 }],
    }));
  });
});
