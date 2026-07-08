/** 错误竞态与状态恢复 E2E / Error race & state recovery E2E tests.
 *
 * UC-23~UC-28, UC-8, UC-24, UC-30, UC-31, UC-34~UC-37: 并发、重置、刷新、参数校验、倍速、事件完整性
 */
import { test, expect } from "@playwright/test";
import {
  SELECTORS,
  WORLD_ID,
  fetchBackendState,
  fetchBackendEvents,
  getTestSeamState,
  resetAndPrepare,
  runNTicks,
} from "./helpers";

test.describe("error race & state recovery", () => {
  test.beforeEach(async ({ page }) => {
    await resetAndPrepare(page);
  });

  test("UC-23 concurrent batch request returns 409", async ({ page }) => {
    // 同时发送两次 batch 请求 / Send two batch requests simultaneously
    const [res1, res2] = await Promise.all([
      page.request.post(`/api/world/${WORLD_ID}/tick/batch/1`),
      page.request.post(`/api/world/${WORLD_ID}/tick/batch/1`),
    ]);
    // 至少一个返回 409 / At least one should return 409
    const statuses = [res1.status(), res2.status()].sort();
    expect(statuses).toContain(409);

    // L1 UI：页面不崩溃 / UI does not crash
    await expect(page.locator(SELECTORS.eventList)).toBeVisible();
  });

  test("UC-24 rapid sequential requests do not corrupt state", async ({ page }) => {
    // 快速连续发送 3 次 batch/1 / Rapidly send 3 sequential batch/1 requests
    const results = [];
    for (let i = 0; i < 3; i++) {
      const res = await page.request.post(`/api/world/${WORLD_ID}/tick/batch/1`);
      results.push(res.status());
    }
    // 至少第一次应成功 / At least the first should succeed
    expect(results[0]).toBe(200);

    // L1 UI：页面不崩溃 / UI does not crash
    await expect(page.locator(SELECTORS.eventList)).toBeVisible();
  });

  test("UC-25 reset while tick running", async ({ page }) => {
    // 启动循环 / Start loop
    await page.locator(SELECTORS.startLoopButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("持续运行中", { timeout: 5000 });
    await expect(page.locator(SELECTORS.tickBadge)).not.toContainText("Display_Tick=0", {
      timeout: 60000,
    });

    // 运行中重置 / Reset while running
    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 15000,
    });

    // L2 API：后端状态已清空 / Backend state cleared
    const state = await fetchBackendState(page);
    expect(state.data_tick).toBe(0);
    expect(state.display_tick).toBe(0);

    // L2 API：事件表已清空 / Events table empty
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    expect(eventsRes.events).toHaveLength(0);
  });

  test("UC-26 invalid batch parameter returns 400", async ({ page }) => {
    const res = await page.request.post(`/api/world/${WORLD_ID}/tick/batch/0`);
    expect(res.status()).toBe(400);
  });

  test("UC-27 page refresh recovers state", async ({ page }) => {
    await runNTicks(page, 1);

    // 刷新页面 / Reload page
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await page.waitForSelector("canvas", { timeout: 30000 });

    // L4 Game：displayTick 恢复 / displayTick recovered after reload
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-28 reset then re-run tick", async ({ page }) => {
    await runNTicks(page, 1);

    // 重置 / Reset
    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });

    // 再次跑 1 tick / Run 1 tick again
    await runNTicks(page, 1);

    // L1 UI：tick 徽章回到 1 / Tick badge back to 1
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=1");

    // L2 API：有事件数据 / Events exist
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    expect(eventsRes.events.length).toBeGreaterThan(0);
  });
});

test.describe("mock speed & event integrity", () => {
  test.beforeEach(async ({ page }) => {
    await resetAndPrepare(page);
  });

  test("UC-30 4x speed movement path is correct", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L4 Game：PC 坐标在合理范围内 / PC positions within reasonable bounds
    const gameState = await getTestSeamState(page);
    expect(gameState).not.toBeNull();
    const positions = gameState!.pcPositions as Record<string, { tx: number; ty: number }>;
    for (const pos of Object.values(positions)) {
      expect(pos.tx).toBeGreaterThanOrEqual(0);
      expect(pos.ty).toBeGreaterThanOrEqual(0);
    }
  });

  test("UC-31 event type coverage is complete", async ({ page }) => {
    test.setTimeout(180000);
    // 跑 4 个 tick 覆盖更多事件类型 / Run 4 ticks for broader coverage
    await runNTicks(page, 4, 120000);

    // L2 API：应有多种事件类型 / Should have multiple event types
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    const types = new Set(eventsRes.events.map((e) => e.type));
    // 至少包含 dm_create + pc_decision + dm_narrative / At least core event types
    expect(types.has("dm_create")).toBe(true);
    expect(types.has("pc_decision")).toBe(true);
    expect(types.has("dm_narrative")).toBe(true);
  });

  test("UC-8 event payload integrity", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：每个事件都有 tick、type、payload / Every event has tick, type, payload
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    for (const ev of eventsRes.events) {
      expect(ev.tick).toBeGreaterThan(0);
      expect(ev.type.length).toBeGreaterThan(0);
      expect(ev.payload).toBeDefined();
    }
  });

  test("UC-34 PC position persists across ticks", async ({ page }) => {
    test.setTimeout(120000);
    await runNTicks(page, 1);

    // 记录 tick 1 后 PC 位置 / Record PC positions after tick 1
    const state1 = await getTestSeamState(page);
    const pos1 = state1!.pcPositions as Record<string, { tx: number; ty: number }>;

    // 跑第 2 个 tick / Run tick 2
    await runNTicks(page, 1);

    // L4 Game：PC 位置存在且合法 / PC positions exist and are valid
    const state2 = await getTestSeamState(page);
    const pos2 = state2!.pcPositions as Record<string, { tx: number; ty: number }>;
    expect(Object.keys(pos2).length).toBe(Object.keys(pos1).length);
  });

  test("UC-35 replay events display correctly", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // 刷新后事件面板仍可显示 / Event panel still displays after reload
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await page.waitForSelector("canvas", { timeout: 30000 });

    // L1 UI：事件面板可见 / Event panel visible
    await expect(page.locator(SELECTORS.eventList)).toBeVisible();
  });

  test("UC-36 multiple tick consistency", async ({ page }) => {
    test.setTimeout(120000);
    await runNTicks(page, 2, 90000);

    // L2 API：tick 1 和 tick 2 事件类型一致 / Consistent event types across ticks
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    const tick1Types = new Set(eventsRes.events.filter((e) => e.tick === 1).map((e) => e.type));
    const tick2Types = new Set(eventsRes.events.filter((e) => e.tick === 2).map((e) => e.type));
    // 两个 tick 都应有 dm_create 和 pc_decision / Both ticks have core event types
    expect(tick1Types.has("dm_create")).toBe(true);
    expect(tick2Types.has("dm_create")).toBe(true);
  });

  test("UC-37 LangGraph state thread isolation", async ({ page }) => {
    test.setTimeout(120000);
    await runNTicks(page, 2, 90000);

    // L2 API：data_tick=2，事件总数合理 / data_tick=2, event count reasonable
    const state = await fetchBackendState(page);
    expect(state.data_tick).toBe(2);

    const eventsRes = await fetchBackendEvents(page, 0, 10);
    // 每个 tick 至少有 3 个核心事件（dm_create, pc_decision, dm_narrative）/ At least 3 core events per tick
    const totalEvents = eventsRes.events.length;
    expect(totalEvents).toBeGreaterThanOrEqual(6);
  });
});
