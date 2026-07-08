/** 控制流与数据一致性 E2E / Control flow & data consistency E2E tests.
 *
 * UC-3, UC-6, UC-7, UC-9, UC-10: 批量 N Tick、暂停恢复、连续数据、tick 同步、数据持久化
 */
import { test, expect } from "@playwright/test";
import {
  SELECTORS,
  fetchBackendState,
  fetchBackendEvents,
  getTestSeamState,
  waitForBackendTick,
  resetAndPrepare,
  runNTicks,
} from "./helpers";

test.describe("control flow & data consistency", () => {
  test.beforeEach(async ({ page }) => {
    await resetAndPrepare(page);
  });

  test("UC-3 run N ticks batch advance", async ({ page }) => {
    test.setTimeout(120000);
    await runNTicks(page, 3, 90000);

    // L2 API：data_tick=3 / Backend data_tick advanced to 3
    const state = await waitForBackendTick(page, 3);
    expect(state.data_tick).toBe(3);

    // L2 API：tick 1~3 均有事件 / Events exist for ticks 1~3
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    const ticks = new Set(eventsRes.events.map((e) => e.tick));
    expect(ticks.has(1)).toBe(true);
    expect(ticks.has(2)).toBe(true);
    expect(ticks.has(3)).toBe(true);

    // L4 Game：displayTick=3 / displayTick advanced to 3
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 3 }));
  });

  test("UC-6 pause and resume loop", async ({ page }) => {
    test.setTimeout(120000);
    await page.locator(SELECTORS.startLoopButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("持续运行中", { timeout: 5000 });
    await expect(page.locator(SELECTORS.tickBadge)).not.toContainText("Display_Tick=0", {
      timeout: 60000,
    });

    // 暂停 / Pause
    await page.locator(SELECTORS.pauseButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("已暂停", { timeout: 10000 });
    const pausedTick = (await getTestSeamState(page))!.displayTick as number;

    // 再次启动循环 / Resume loop
    await page.locator(SELECTORS.startLoopButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("持续运行中", { timeout: 5000 });

    // 等待 tick 继续增长 / Wait for tick to grow beyond paused tick
    await expect(page.locator(SELECTORS.tickBadge)).not.toContainText(
      `Display_Tick=${pausedTick}`,
      { timeout: 60000 }
    );

    // 清理：暂停循环 / Cleanup: pause loop
    await page.locator(SELECTORS.pauseButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("已暂停", { timeout: 10000 });
  });

  test("UC-7 consecutive tick data not lost", async ({ page }) => {
    test.setTimeout(120000);
    await runNTicks(page, 2, 90000);

    // L2 API：tick 1 和 tick 2 均有事件 / Both tick 1 and 2 have events
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    const tick1Events = eventsRes.events.filter((e) => e.tick === 1);
    const tick2Events = eventsRes.events.filter((e) => e.tick === 2);
    expect(tick1Events.length).toBeGreaterThan(0);
    expect(tick2Events.length).toBeGreaterThan(0);
  });

  test("UC-9 display tick syncs with data tick", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：data_tick === display_tick / Backend ticks synchronized
    const state = await fetchBackendState(page);
    expect(state.data_tick).toBe(state.display_tick);

    // L4 Game：displayTick = 后端 display_tick / Game displayTick matches backend
    const gameState = await getTestSeamState(page);
    expect(gameState!.displayTick).toBe(state.display_tick);
  });

  test("UC-10 character data persistence", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // L2 API：pcs/actors/scene_objects 完整 / API returns complete data
    const state = await fetchBackendState(page);
    expect(state.pcs.length).toBeGreaterThan(0);
    expect(state.scene_objects.length).toBeGreaterThan(0);

    // L4 Game：PC 精灵已创建 / PC sprites created
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(
        expect.objectContaining({
          sceneBuilt: true,
          pcCount: state.pcs.length,
        })
      );
  });
});
