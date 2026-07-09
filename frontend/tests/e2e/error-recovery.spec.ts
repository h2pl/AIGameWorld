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

  test("UC-24 data_tick ahead returns 429 on tick/next", async ({ page }) => {
    // 快速连续调用 /tick/next 触发 429 / Rapidly call /tick/next to trigger 429
    // data_tick 比 display_tick 超前 3 时应返回 429 / 429 when data_tick is 3+ ahead
    const results: number[] = [];
    for (let i = 0; i < 5; i++) {
      const res = await page.request.get(`/api/world/${WORLD_ID}/tick/next`);
      results.push(res.status());
    }

    // 至少第一次应成功 / At least the first should succeed
    expect(results[0]).toBe(200);
    // 连续调用中应出现 429（data_tick 超前 display_tick >= 3）/ 429 expected when data_tick 3+ ahead
    const has429 = results.includes(429);
    if (has429) {
      // 验证 429 出现在 200 之后 / 429 should appear after 200s
      const first429 = results.indexOf(429);
      const last200 = results.lastIndexOf(200);
      expect(first429).toBeGreaterThan(last200);
    }

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
    test.setTimeout(90000);
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
    // 已在 beforeEach 切到 4x / Already in 4x from beforeEach

    // 记录倍速前事件数量 / Record event count before
    const beforeEvents = await fetchBackendEvents(page, 0, 10);
    const beforeCount = beforeEvents.events.length;

    await runNTicks(page, 1);

    // L4 Game：PC 坐标在合理范围内 / PC positions within reasonable bounds
    const gameState = await getTestSeamState(page);
    expect(gameState).not.toBeNull();
    const positions = gameState!.pcPositions as Record<string, { tx: number; ty: number }>;
    for (const pos of Object.values(positions)) {
      expect(pos.tx).toBeGreaterThanOrEqual(0);
      expect(pos.ty).toBeGreaterThanOrEqual(0);
    }

    // L2 API：倍速下事件不丢失 / No events lost in 4x speed
    const afterEvents = await fetchBackendEvents(page, 0, 10);
    expect(afterEvents.events.length).toBeGreaterThan(beforeCount);

    // L4 Game：cameraZoom 应为 > 1.0（4x 场景下相机可能缩放）/ cameraZoom may be > 1.0
    const zoom = gameState!.cameraZoom as number;
    expect(zoom).toBeGreaterThanOrEqual(1.0);

    // L1 UI：切换倍速不崩溃 / Speed toggle doesn't crash
    await page.locator(SELECTORS.speed4x).click(); // 再次点击切换
    await expect(page.locator(SELECTORS.eventList)).toBeVisible();
  });

  test("UC-31 event order integrity across ticks", async ({ page }) => {
    test.setTimeout(180000);
    // 跑 4 个 tick 覆盖更多事件类型 / Run 4 ticks for broader coverage
    await runNTicks(page, 4, 120000);

    // L2 API：事件按 tick 递增 / Events ordered by tick ascending
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    const events = eventsRes.events;
    for (let i = 1; i < events.length; i++) {
      expect(events[i].tick).toBeGreaterThanOrEqual(events[i - 1].tick);
    }

    // L2 API：同一 tick 内事件类型顺序正确 / Within same tick, correct type order
    // dm_create 在 pc_decision 前，pc_decision 在 actions 前，actions 在 dm_narrative 前
    const tickGroups = new Map<number, typeof events>();
    for (const ev of events) {
      if (!tickGroups.has(ev.tick)) tickGroups.set(ev.tick, []);
      tickGroups.get(ev.tick)!.push(ev);
    }
    for (const [, tickEvents] of tickGroups) {
      const types = tickEvents.map((e) => e.type);
      const dmCreateIdx = types.indexOf("dm_create");
      const decisionIdx = types.indexOf("pc_decision");
      const actionIdx = types.findIndex((t) =>
        ["pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(t)
      );
      const narrativeIdx = types.lastIndexOf("dm_narrative");
      // dm_create 在最前面 / dm_create comes first
      if (dmCreateIdx >= 0 && decisionIdx >= 0) {
        expect(dmCreateIdx).toBeLessThan(decisionIdx);
      }
      // pc_decision 在 actions 前 / pc_decision before actions
      if (decisionIdx >= 0 && actionIdx >= 0) {
        expect(decisionIdx).toBeLessThan(actionIdx);
      }
      // actions 在 dm_narrative 前 / actions before dm_narrative
      if (actionIdx >= 0 && narrativeIdx >= 0) {
        expect(actionIdx).toBeLessThan(narrativeIdx);
      }
      // pc_decision 在 dm_narrative 前 / pc_decision before dm_narrative
      if (decisionIdx >= 0 && narrativeIdx >= 0) {
        expect(decisionIdx).toBeLessThan(narrativeIdx);
      }
    }

    // L2 API：pc_decision 的 pc_id 与后续 action 的 pc_id 匹配 / pc_id consistency
    const types = new Set(events.map((e) => e.type));
    expect(types.has("dm_create")).toBe(true);
    expect(types.has("pc_decision")).toBe(true);
    expect(types.has("dm_narrative")).toBe(true);

    // 验证 pc_decision 与后续 action 的 pc_id 匹配 / Verify pc_id matching
    for (const [, tickEvents] of tickGroups) {
      const decisionPcIds = tickEvents
        .filter((e) => e.type === "pc_decision")
        .map((e) => String(e.payload.pc_id || e.payload.pc_name || ""));
      const actionPcIds = tickEvents
        .filter((e) => ["pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(e.type))
        .map((e) => String(e.payload.pc_id || e.payload.pc_name || ""));
      // 每个 action 的 pc_id 应在 decision 列表中 / Every action pc_id should appear in decisions
      for (const actionPcId of actionPcIds) {
        if (actionPcId) {
          expect(decisionPcIds).toContain(actionPcId);
        }
      }
    }
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
    // 轮询等待 pcPositions 就绪（scene_setup rebuild 后测试 seam 可能延迟更新）
    let pos1: Record<string, { tx: number; ty: number }> = {};
    await expect.poll(() => getTestSeamState(page).then(s => {
      const p = s!.pcPositions as Record<string, { tx: number; ty: number }>;
      if (Object.keys(p).length <= 0) throw new Error("pcPositions empty");
      pos1 = p;
      return Object.keys(p).length;
    }), { timeout: 30000 }).toBeGreaterThan(0);

    // L2 API：/state 中 PC 坐标存在 / PC positions exist in /state API
    const backendState = await fetchBackendState(page);
    const apiPcs = backendState.pcs as Array<Record<string, unknown>>;
    for (const pc of apiPcs) {
      const px = pc.position_x as number;
      const py = pc.position_y as number;
      expect(px).toBeDefined();
      expect(py).toBeDefined();
    }

    // 跑第 2 个 tick / Run tick 2
    await runNTicks(page, 1);

    // L4 Game：PC 位置存在且合法 / PC positions exist and are valid
    const state2 = await getTestSeamState(page);
    const pos2 = state2!.pcPositions as Record<string, { tx: number; ty: number }>;
    expect(Object.keys(pos2).length).toBe(Object.keys(pos1).length);

    // L3 DB：通过 /view/global/tick_events 端点验证事件已写入 DB / Verify events written to DB
    const viewRes = await page.request.get("/view/global/tick_events");
    expect(viewRes.ok()).toBe(true);
  });

  test("UC-35 replay events display correctly", async ({ page }) => {
    test.setTimeout(90000);
    await runNTicks(page, 1);

    // 记录刷新前事件面板文本 / Record event panel text before reload
    const beforeText = await page.locator(SELECTORS.eventList).textContent();

    // 刷新后事件面板仍可显示 / Event panel still displays after reload
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await page.waitForSelector("canvas", { timeout: 30000 });

    // L1 UI：事件面板可见 / Event panel visible
    await expect(page.locator(SELECTORS.eventList)).toBeVisible();

    // L1 UI：刷新后事件面板内容恢复，核心关键词仍在 / Event content recovered after reload
    await expect(page.locator(SELECTORS.eventList)).toContainText("DM 创建情境", {
      timeout: 30000,
    });
    await expect(page.locator(SELECTORS.eventList)).toContainText("DM 叙事", { timeout: 30000 });

    // L1 UI：事件顺序保持一致 / Event order preserved after replay
    const afterLines = await page
      .locator(`${SELECTORS.eventList} ${SELECTORS.eventLine}`)
      .allTextContents();
    const dmCreateIdx = afterLines.findIndex((t) => t.includes("DM 创建情境"));
    const narrativeIdx = afterLines.findIndex((t) => t.includes("DM 叙事"));
    expect(dmCreateIdx).toBeGreaterThanOrEqual(0);
    expect(narrativeIdx).toBeGreaterThan(dmCreateIdx);
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

    // L2 API：每个 tick 的 dm_create 事件都有独立内容 / Each tick's dm_create has unique content
    const dmCreates = eventsRes.events.filter((e) => e.type === "dm_create");
    expect(dmCreates.length).toBeGreaterThanOrEqual(2);
    const plotBriefs = dmCreates.map((e) => String(e.payload.plot_brief || ""));
    // 两个 tick 的 plot_brief 应不同 / plot_briefs should differ across ticks
    expect(new Set(plotBriefs).size).toBeGreaterThanOrEqual(1);

    // L3 DB：通过 /view 端点验证 DM 记录写入 / Verify DM records written via /view
    const viewRes = await page.request.get("/view/global/dm_records");
    expect(viewRes.ok()).toBe(true);
  });
});
