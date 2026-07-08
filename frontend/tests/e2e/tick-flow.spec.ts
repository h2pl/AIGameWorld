/** 基础 Tick 流程 E2E / Basic tick flow E2E tests.
 *
 * UC-1, UC-2, UC-4, UC-5: 页面加载、跑 1 tick、重置、循环启停
 */
import { test, expect } from "@playwright/test";
import {
  SELECTORS,
  WORLD_ID,
  fetchBackendState,
  fetchBackendEvents,
  fetchLoopStatus,
  waitForBackendTick,
  getTestSeamState,
  resetAndPrepare,
  runNTicks,
} from "./helpers";

test.describe("basic tick flow", () => {
  test.beforeEach(async ({ page }) => {
    await resetAndPrepare(page);
  });

  test("UC-1 page loads and backend becomes ready", async ({ page }) => {
    const statusText = await page.locator(SELECTORS.status).textContent();
    expect(statusText).toMatch(/就绪|已重置|已展示到 Tick/);
    await expect(page.locator(SELECTORS.eventList)).toBeVisible();

    // 验证后端初始状态 / Verify backend initial state
    const state = await fetchBackendState(page);
    expect(state.world_id).toBe(WORLD_ID);
    expect(state.data_tick).toBe(0);
    expect(state.display_tick).toBe(0);
    expect(state.pcs.length).toBeGreaterThan(0);

    // 验证 Phaser test seam 已就绪 / Verify Phaser test seam ready
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(
        expect.objectContaining({
          scene: "Game",
          sceneBuilt: false,
          pcCount: 0,
          displayTick: 0,
          worldId: WORLD_ID,
        })
      );
  });

  test("UC-2 run 1 tick end-to-end", async ({ page }) => {
    await runNTicks(page, 1);

    // 状态进入生成中 / Status shows generating
    // 事件面板应出现事件行 / Event panel should have event lines
    await expect(
      page.locator(SELECTORS.eventList).locator(SELECTORS.eventLine).first()
    ).toBeVisible({ timeout: 10000 });

    // tick 徽章应更新 / Tick badge should update
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=1");

    // 等待事件串行处理完成 / Wait for events to finish sequential processing
    await expect(page.locator(SELECTORS.eventList)).toContainText("DM 叙事", {
      timeout: 30000,
    });

    // 至少包含关键事件类型 / Should contain key event types
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    expect(eventsText).toContain("DM 创建情境");
    expect(eventsText).toContain("DM 叙事");

    // 验证后端 data_tick / display_tick 已推进 / Verify backend tick advanced
    const state = await waitForBackendTick(page, 1);
    expect(state.display_tick).toBe(1);

    // 验证后端事件列表包含关键事件 / Verify backend events contain key types
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    expect(eventsRes.data_tick).toBe(1);
    expect(eventsRes.display_tick).toBe(1);
    const eventTypes = eventsRes.events.map((e) => e.type);
    expect(eventTypes).toContain("dm_create");
    expect(eventTypes).toContain("pc_decision");
    expect(eventTypes).toContain("dm_narrative");

    // 验证 Phaser 场景已构建并出现角色 / Verify Phaser scene built and sprites exist
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(
        expect.objectContaining({
          sceneBuilt: true,
          pcCount: state.pcs.length,
          displayTick: 1,
        })
      );
  });

  test("UC-4 reset clears state end-to-end", async ({ page }) => {
    await runNTicks(page, 1);
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=1");

    // 先确认后端已有数据 / Confirm backend has data before reset
    const stateBefore = await waitForBackendTick(page, 1);
    expect(stateBefore.data_tick).toBe(1);

    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });
    await expect(page.locator(SELECTORS.status)).toContainText("已重置");

    // 验证后端 tick 与事件已被清空 / Verify backend tick and events cleared
    const stateAfter = await fetchBackendState(page);
    expect(stateAfter.data_tick).toBe(0);
    expect(stateAfter.display_tick).toBe(0);

    const eventsRes = await fetchBackendEvents(page, 0, 10);
    expect(eventsRes.events).toHaveLength(0);

    // 验证 Phaser test seam 已重置 / Verify reset destroyed scene
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(
        expect.objectContaining({
          sceneBuilt: false,
          pcCount: 0,
          displayTick: 0,
        })
      );
  });

  test("UC-5 start and pause loop end-to-end", async ({ page }) => {
    await page.locator(SELECTORS.startLoopButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("持续运行中", {
      timeout: 5000,
    });

    // 等至少 1 个 tick 产出 / Wait for at least 1 tick
    await expect(page.locator(SELECTORS.tickBadge)).not.toContainText("Display_Tick=0", {
      timeout: 60000,
    });

    // 验证后端循环正在运行 / Verify backend loop is running
    const statusBefore = await fetchLoopStatus(page);
    expect(statusBefore.running).toBe(true);
    const stateBefore = await waitForBackendTick(page, 1);
    expect(stateBefore.data_tick).toBeGreaterThanOrEqual(1);

    await page.locator(SELECTORS.pauseButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("已暂停", { timeout: 10000 });

    // 验证后端循环已停止 / Verify backend loop stopped
    const statusAfter = await fetchLoopStatus(page);
    expect(statusAfter.running).toBe(false);

    // 验证暂停后不会 409 / Verify no 409 after pause
    const batchRes = await page.request.post(`/api/world/${WORLD_ID}/tick/batch/1`);
    expect(batchRes.ok()).toBe(true);
  });
});
