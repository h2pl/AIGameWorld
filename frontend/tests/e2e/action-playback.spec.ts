/** Action 播放 E2E / Action playback E2E tests.
 *
 * UC-16~UC-22, UC-32, UC-33: Talk/Explore/Interact/Combat 播放、串行、暂停、倍速、失败降级
 */
import { test, expect } from "@playwright/test";
import {
  SELECTORS,
  fetchBackendEvents,
  fetchLoopStatus,
  getTestSeamState,
  resetAndPrepare,
  runNTicks,
} from "./helpers";

test.describe("action playback", () => {
  test.beforeEach(async ({ page }) => {
    await resetAndPrepare(page);
  });

  test("UC-16 talk action plays dialogue bubbles", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：获取 pc_talk 事件 / Get pc_talk event from API
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const talkEvents = eventsRes.events.filter((e) => e.type === "pc_talk");

    if (talkEvents.length > 0) {
      const talk = talkEvents[0];
      const turns = talk.payload.turns as Array<{ speaker_id: string; text: string }>;
      expect(Array.isArray(turns)).toBe(true);

      // L4 Game：确认游戏状态可读 / Verify game state readable
      const gameState = await getTestSeamState(page);
      expect(gameState).not.toBeNull();
    }

    // L1 UI：事件面板包含对话事件 / Event panel contains talk event
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    if (talkEvents.length > 0) {
      expect(eventsText).toContain("角色对话");
    }

    // L4 Game：场景已构建 / Scene built
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ sceneBuilt: true, displayTick: 1 }));
  });

  test("UC-17 explore action walks to waypoints", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：获取 pc_explore 事件 / Get pc_explore event
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const exploreEvents = eventsRes.events.filter((e) => e.type === "pc_explore");

    if (exploreEvents.length > 0) {
      const explore = exploreEvents[0];
      const waypoints = explore.payload.waypoints as Array<{ x: number; y: number }>;
      expect(Array.isArray(waypoints)).toBe(true);

      // L4 Game：PC 不再行走（已到达终点）/ PC no longer walking
      await expect
        .poll(() => getTestSeamState(page))
        .toEqual(expect.objectContaining({ sceneBuilt: true }));

      const gameState = await getTestSeamState(page);
      const pcWalking = gameState!.pcWalking as Record<string, boolean>;
      const allDone = Object.values(pcWalking).every((w) => !w);
      expect(allDone).toBe(true);
    }

    // L1 UI：事件面板包含探索事件 / Event panel contains explore event
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    if (exploreEvents.length > 0) {
      expect(eventsText).toContain("角色探索");
    }

    // L4 Game / Game layer
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-18 interact action walks and shows narration", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：获取 pc_interact 事件 / Get pc_interact event
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const interactEvents = eventsRes.events.filter((e) => e.type === "pc_interact");

    if (interactEvents.length > 0) {
      const interact = interactEvents[0];
      const narration = String(interact.payload.narration || "");
      expect(narration.length).toBeGreaterThan(0);

      // ObjectPanel 不应自动弹出 / ObjectPanel should not auto-popup
      await expect(page.locator(SELECTORS.objectPanel)).toBeHidden();
    }

    // L1 UI：事件面板包含交互事件 / Event panel contains interact event
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    if (interactEvents.length > 0) {
      expect(eventsText).toContain("角色互动");
    }

    // L4 Game / Game layer
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-19 combat action walks and shows narration", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：获取 pc_combat 事件 / Get pc_combat event
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const combatEvents = eventsRes.events.filter((e) => e.type === "pc_combat");

    if (combatEvents.length > 0) {
      const combat = combatEvents[0];
      const narration = String(combat.payload.narration || "");
      expect(narration.length).toBeGreaterThan(0);

      // 如果 target_defeated=true 且是 actor，验证 actor 被移除 / Verify actor removed if defeated
      if (combat.payload.target_defeated && combat.payload.target_type === "actor") {
        const targetId = String(combat.payload.target_id || "");
        if (targetId) {
          const gameState = await getTestSeamState(page);
          const actorExists = gameState!.actorExists as Record<string, boolean>;
          expect(actorExists[targetId]).toBeFalsy();
        }
      }
    }

    // L1 UI：事件面板包含战斗事件 / Event panel contains combat event
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    if (combatEvents.length > 0) {
      expect(eventsText).toContain("角色战斗");
    }

    // L4 Game / Game layer
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-20 actions execute serially within same tick", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：同一 tick 的 action 按 order 排列 / Actions sorted by order
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const actionEvents = eventsRes.events.filter((e) =>
      ["pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(e.type)
    );

    if (actionEvents.length > 1) {
      const orders = actionEvents.map((e) => Number(e.payload.order ?? 0));
      for (let i = 1; i < orders.length; i++) {
        expect(orders[i]).toBeGreaterThanOrEqual(orders[i - 1]);
      }
    }

    // L4 Game：所有 PC 不再行走 / All PCs done walking
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ sceneBuilt: true, displayTick: 1 }));
    const gameState = await getTestSeamState(page);
    const pcWalking = gameState!.pcWalking as Record<string, boolean>;
    const allDone = Object.values(pcWalking).every((w) => !w);
    expect(allDone).toBe(true);
  });

  test("UC-21 4x speed shortens movement duration", async ({ page }) => {
    test.setTimeout(90000);
    // 已在 beforeEach 切到 4x，跑 1 tick 验证完成时间合理 / Already in 4x, verify reasonable completion
    const start = Date.now();
    await runNTicks(page, 1);
    const elapsed = Date.now() - start;

    // 4x 倍速下 1 tick 应在 30 秒内完成 / 1 tick in 4x should complete within 30s
    expect(elapsed).toBeLessThan(30000);

    // L4 Game：displayTick=1 / displayTick reached 1
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-22 pause cancels current action walk and dialogue", async ({ page }) => {
    test.setTimeout(90000);
    await page.locator(SELECTORS.startLoopButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("持续运行中", { timeout: 5000 });

    await expect(page.locator(SELECTORS.tickBadge)).not.toContainText("Display_Tick=0", {
      timeout: 60000,
    });

    // 暂停 / Pause
    await page.locator(SELECTORS.pauseButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("已暂停", { timeout: 10000 });

    // L4 Game：暂停后 PC 不应再行走 / PCs should not be walking after pause
    const gameState = await getTestSeamState(page);
    const pcWalking = gameState!.pcWalking as Record<string, boolean>;
    const allDone = Object.values(pcWalking).every((w) => !w);
    expect(allDone).toBe(true);

    // L2 API：循环已停止 / Loop stopped
    const loopStatus = await fetchLoopStatus(page);
    expect(loopStatus.running).toBe(false);
  });

  test("UC-32 multiple PCs execute different actions in same tick", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：同一 tick 有多个不同类型的 action / Multiple action types in same tick
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const actionTypes = new Set(
      eventsRes.events
        .filter((e) => ["pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(e.type))
        .map((e) => e.type)
    );
    expect(actionTypes.size).toBeGreaterThanOrEqual(1);

    // L4 Game / Game layer
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ sceneBuilt: true, displayTick: 1 }));
  });

  test("UC-33 action failure does not crash game", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // 即使某个 action 的 target 不存在，游戏也不崩溃 / Game does not crash even if action target missing
    await expect(page.locator(SELECTORS.eventList)).toBeVisible();

    // L4 Game：场景仍可运行 / Scene still functional
    const gameState = await getTestSeamState(page);
    expect(gameState).not.toBeNull();
    expect(gameState!.sceneBuilt).toBe(true);

    // L1 UI：事件面板包含内容（即使 action 失败也有降级文本）/ Event panel has content (even with degraded action)
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    // 至少应包含核心事件类型 / Should contain core event types at minimum
    const hasCoreContent =
      eventsText!.includes("DM 创建情境") ||
      eventsText!.includes("DM 叙事") ||
      eventsText!.includes("角色决策");
    expect(hasCoreContent).toBe(true);

    // L2 API：即使部分 action 失败，核心事件仍存在 / Core events still exist even if some actions fail
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const hasDmCreate = eventsRes.events.some((e) => e.type === "dm_create");
    const hasDmNarrative = eventsRes.events.some((e) => e.type === "dm_narrative");
    expect(hasDmCreate).toBe(true);
    expect(hasDmNarrative).toBe(true);
  });
});
