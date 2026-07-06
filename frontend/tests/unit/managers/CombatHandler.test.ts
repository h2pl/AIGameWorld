// --- 测试 / Tests ---
/** CombatHandler 单元测试 / Combat event handler unit tests */
import { describe, it, expect, vi } from "vitest";
import { CombatHandler } from "../../../src/managers/event_handler/CombatHandler";
import type { CharacterSprite } from "../../../src/gameobjects/CharacterSprite";
import type { EventData } from "../../../src/types";

function makeSprite(id: string) {
  return {
    id,
    rawSprite: { id },
    showExploreRecord: vi.fn((_text: string, onHide?: () => void) => {
      onHide?.();
    }),
  } as unknown as CharacterSprite;
}

function makeMovementManager() {
  return {
    walkTo: vi.fn(
      (
        _sprite: CharacterSprite,
        tx: number,
        ty: number,
        opts?: { onComplete?: (x: number, y: number) => void }
      ) => {
        opts?.onComplete?.(tx, ty);
      }
    ),
  };
}

function makeActorManager() {
  return {
    remove: vi.fn(),
  };
}

function makeEvent(payload: Record<string, unknown>): EventData {
  return { type: "pc_combat", tick: 1, payload };
}

describe("CombatHandler", () => {
  it("should walk to target and show combat narration", async () => {
    const sprite = makeSprite("pc1");
    const mm = makeMovementManager();
    const follow = vi.fn();
    const handler = new CombatHandler(
      () => sprite,
      () => mm as any,
      () => makeActorManager() as any,
      follow
    );

    await handler.handle(
      makeEvent({
        pc_id: "pc1",
        waypoints: [
          { x: 0, y: 0 },
          { x: 3, y: 4 },
        ],
        narration: "他一剑劈向地精。",
      })
    );

    expect(follow).toHaveBeenCalledWith(sprite.rawSprite);
    expect(mm.walkTo).toHaveBeenCalledWith(sprite, 3, 4, expect.any(Object));
    expect(sprite.showExploreRecord).toHaveBeenCalledWith("他一剑劈向地精。", expect.any(Function));
  });

  it("should show narration even without waypoints", async () => {
    const sprite = makeSprite("pc1");
    const mm = makeMovementManager();
    const handler = new CombatHandler(
      () => sprite,
      () => mm as any,
      () => makeActorManager() as any,
      vi.fn()
    );

    await handler.handle(makeEvent({ pc_id: "pc1", waypoints: [], narration: "战斗结束。" }));

    expect(mm.walkTo).not.toHaveBeenCalled();
    expect(sprite.showExploreRecord).toHaveBeenCalledWith("战斗结束。", expect.any(Function));
  });

  it("should remove defeated actor from scene", async () => {
    const sprite = makeSprite("pc1");
    const mm = makeMovementManager();
    const actorManager = makeActorManager();
    const handler = new CombatHandler(
      () => sprite,
      () => mm as any,
      () => actorManager as any,
      vi.fn()
    );

    await handler.handle(
      makeEvent({
        pc_id: "pc1",
        target_id: "goblin",
        target_type: "actor",
        target_defeated: true,
        narration: "地精倒地不起。",
      })
    );

    expect(actorManager.remove).toHaveBeenCalledWith("goblin");
  });

  it("should not remove target when not defeated", async () => {
    const sprite = makeSprite("pc1");
    const actorManager = makeActorManager();
    const handler = new CombatHandler(
      () => sprite,
      () => makeMovementManager() as any,
      () => actorManager as any,
      vi.fn()
    );

    await handler.handle(
      makeEvent({
        pc_id: "pc1",
        target_id: "goblin",
        target_type: "actor",
        target_defeated: false,
        narration: "地精后退了几步。",
      })
    );

    expect(actorManager.remove).not.toHaveBeenCalled();
  });

  it("should skip when payload is missing", async () => {
    const handler = new CombatHandler(
      () => makeSprite("pc1"),
      () => makeMovementManager() as any,
      () => makeActorManager() as any,
      vi.fn()
    );
    const spy = vi.fn();
    await handler.handle({ type: "pc_combat", tick: 1 });
    expect(spy).not.toHaveBeenCalled();
  });

  it("should skip when pc_id is missing", async () => {
    const handler = new CombatHandler(
      () => makeSprite("pc1"),
      () => makeMovementManager() as any,
      () => makeActorManager() as any,
      vi.fn()
    );
    await handler.handle(makeEvent({ waypoints: [{ x: 1, y: 1 }] }));
    expect(handler).toBeDefined();
  });

  it("should skip when sprite is not found", async () => {
    const mm = makeMovementManager();
    const handler = new CombatHandler(
      () => undefined,
      () => mm as any,
      () => makeActorManager() as any,
      vi.fn()
    );
    await handler.handle(makeEvent({ pc_id: "pc1", narration: "..." }));
    expect(mm.walkTo).not.toHaveBeenCalled();
  });

  it("should skip when movement manager is not available", async () => {
    const sprite = makeSprite("pc1");
    const handler = new CombatHandler(
      () => sprite,
      () => undefined,
      () => makeActorManager() as any,
      vi.fn()
    );
    await handler.handle(
      makeEvent({ pc_id: "pc1", waypoints: [{ x: 1, y: 1 }], narration: "..." })
    );
    expect(sprite.showExploreRecord).not.toHaveBeenCalled();
  });
});
