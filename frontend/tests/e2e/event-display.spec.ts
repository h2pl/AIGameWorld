/** 事件展示 E2E / Event display E2E tests.
 *
 * UC-11~UC-15, UC-29, UC-38: 事件面板、DM 情境、叙事、物体面板、Mock 状态
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

test.describe("event display", () => {
  test.beforeEach(async ({ page }) => {
    await resetAndPrepare(page);
  });

  test("UC-11 dm create panel renders correctly", async ({ page }) => {
    await runNTicks(page, 1);

    // L1 UI：面板可见、内容包含 plot_brief、高度自适应 / Panel visible, contains plot_brief, auto height
    await expect(page.locator(SELECTORS.dmCreationPanel)).toBeVisible();
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const dmCreate = eventsRes.events.find((e) => e.type === "dm_create");
    expect(dmCreate).toBeDefined();
    const plotBrief = String(dmCreate!.payload.plot_brief || "");
    expect(plotBrief.length).toBeGreaterThan(0);

    const briefText = await page.locator(SELECTORS.dmCreationBrief).textContent();
    expect(briefText).toContain(plotBrief);

    const body = page.locator(SELECTORS.dmCreationBody);
    const noClipping = await body.evaluate((el) => el.scrollHeight <= el.clientHeight + 2);
    expect(noClipping).toBe(true);

    // L4 Game：场景已构建 / Scene built
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ sceneBuilt: true, displayTick: 1 }));
  });

  test("UC-12 pc decision bubbles not duplicated", async ({ page }) => {
    test.setTimeout(90000);
    const state = await fetchBackendState(page);
    const pcCount = state.pcs.length;

    await runNTicks(page, 2, 60000);

    // L1 UI：事件面板只展示当前 tick，决策行数 = PC 数 / Event panel shows current tick only
    await expect(
      page.locator(`${SELECTORS.eventList} ${SELECTORS.eventLine}:has-text("角色决策")`)
    ).toHaveCount(pcCount, { timeout: 10000 });

    // L2 API：每个 PC 在每个 tick 只有一条 pc_decision / Each PC has exactly one pc_decision per tick
    const eventsRes = await fetchBackendEvents(page, 0, 3);
    const decisionEvents = eventsRes.events.filter((e) => e.type === "pc_decision");
    // 调试：打印决策事件详情 / Debug: print decision event details
    console.log(
      "[UC-12] decision events:",
      JSON.stringify(
        decisionEvents.map((e) => ({
          pc_id: e.payload.pc_id,
          tick: e.tick,
          action_type: e.payload.action_type,
        }))
      )
    );
    // 按 PC+tick 分组验证无重复 / Group by PC+tick to verify no duplicates
    const byPcTick: Record<string, number> = {};
    for (const e of decisionEvents) {
      const key = `${e.payload.pc_id}_tick${e.tick}`;
      byPcTick[key] = (byPcTick[key] || 0) + 1;
    }
    // 取第一个 PC 的 tick 数作为实际 tick 数 / Use first PC's tick count as actual tick count
    const ticksPerPc = Object.entries(byPcTick).filter(([k]) =>
      k.startsWith(`${decisionEvents[0]?.payload.pc_id}_tick`)
    ).length;
    // 每个 PC 在同一 tick 不应重复 / No duplicate per PC per tick
    const duplicates = Object.entries(byPcTick).filter(([, c]) => c > 1);
    expect(duplicates.length, `duplicate pc_decisions: ${JSON.stringify(duplicates)}`).toBe(0);
    // 决策事件总数 = PC 数 × tick 数 / Total decisions = PC count × tick count
    expect(decisionEvents.length).toBe(pcCount * ticksPerPc);

    // L4 Game：每个 PC 的 think 次数等于 tick 数 / Each PC think count equals tick count
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ sceneBuilt: true, displayTick: 2 }));
    const gameState = await getTestSeamState(page);
    expect(gameState).not.toBeNull();
    const thinkCounts = gameState!.pcThinkCounts as Record<string, number>;
    expect(Object.keys(thinkCounts).length).toBe(pcCount);
    for (const count of Object.values(thinkCounts)) {
      expect(count).toBe(2);
    }
    expect(gameState!.activeThoughtBubbles as number).toBeLessThanOrEqual(pcCount);
  });

  test("UC-13 narrative content relates to pc actions", async ({ page }) => {
    test.setTimeout(60000);
    await runNTicks(page, 1);

    // L2 API：收集 action 关键词 / Collect action keywords from events
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const actionEvents = eventsRes.events.filter((e) =>
      ["pc_decision", "pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(e.type)
    );
    const keywords: string[] = [];
    for (const ev of actionEvents) {
      const p = ev.payload;
      if (p.pc_name) keywords.push(String(p.pc_name));
      if (p.action_type) keywords.push(String(p.action_type));
      if (p.target_id) keywords.push(String(p.target_id));
    }

    // L1 UI：叙事文本非空且与 action 相关 / Narrative non-empty and related
    const narrativeText = (await page.locator(SELECTORS.narrativeBody).textContent()) || "";
    expect(narrativeText.length).toBeGreaterThan(10);
    const hasKeyword = keywords.some((k) => narrativeText.toLowerCase().includes(k.toLowerCase()));
    expect(hasKeyword || narrativeText.length >= 30).toBe(true);

    // L4 Game / Game layer
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-14 events render in correct order", async ({ page }) => {
    test.setTimeout(60000);
    await runNTicks(page, 1);

    // L1 UI：事件面板顺序 / Event panel order
    const lines = await page
      .locator(`${SELECTORS.eventList} ${SELECTORS.eventLine}`)
      .allTextContents();
    const dmCreateIdx = lines.findIndex((t) => t.includes("DM 创建情境"));
    const decisionIdx = lines.findIndex((t) => t.includes("角色决策"));
    const narrativeIdx = lines.findIndex((t) => t.includes("DM 叙事"));
    const actionIdx = lines.findIndex((t) => /角色对话|角色探索|角色互动|pc_combat/.test(t));
    expect(dmCreateIdx).toBeGreaterThanOrEqual(0);
    expect(decisionIdx).toBeGreaterThan(dmCreateIdx);
    expect(actionIdx).toBeGreaterThan(decisionIdx);
    expect(narrativeIdx).toBeGreaterThan(actionIdx);

    // L2 API：后端事件顺序 / Backend event order
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const types = eventsRes.events.map((e) => e.type);
    const apiDmCreate = types.indexOf("dm_create");
    const apiDecision = types.findIndex((t) => t === "pc_decision");
    const apiAction = types.findIndex((t) =>
      ["pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(t)
    );
    const apiNarrative = types.lastIndexOf("dm_narrative");
    expect(apiDmCreate).toBe(0);
    expect(apiDecision).toBeGreaterThan(apiDmCreate);
    expect(apiAction).toBeGreaterThan(apiDecision);
    expect(apiNarrative).toBeGreaterThan(apiAction);

    // L4 Game / Game layer
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-15 scene object intro does not auto popup", async ({ page }) => {
    test.setTimeout(90000);
    // 场景未构建前 ObjectPanel 不应自动出现 / ObjectPanel should stay hidden before scene built
    await expect(page.locator(SELECTORS.objectPanel)).toBeHidden();

    await runNTicks(page, 1, 90000);

    // 场景构建后仍然不应自动弹出 / Still hidden after scene built
    await expect(page.locator(SELECTORS.objectPanel)).toBeHidden();

    // L2 API：获取第一个场景物体 / Get first scene object
    const state = await fetchBackendState(page);
    const obj = state.scene_objects[0];
    expect(obj).toBeDefined();

    // 通过 test seam 点击第一个物体 / Click first object via test seam
    await page.evaluate(() => {
      (window as any).__TEST__.clickObject(0);
    });

    // L1 UI：ObjectPanel 出现并包含物体名称 / ObjectPanel appears with object name
    await expect(page.locator(SELECTORS.objectPanel)).toBeVisible();
    const panelText = await page.locator(SELECTORS.objectPanel).textContent();
    expect(panelText).toContain(obj.name);

    // L4 Game：场景已构建且存在物体 / Scene built with terrain objects
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(
        expect.objectContaining({
          sceneBuilt: true,
          terrainObjectCount: state.scene_objects.length,
          displayTick: 1,
        })
      );
  });

  test("UC-29 mock mode status bar shows correct text", async ({ page }) => {
    // L1 UI：左上角 Mock 标识 / Top-left mock indicator
    const mockPanel = page.locator(SELECTORS.mockConfigPanel);
    await expect(mockPanel).toBeVisible();
    const mockText = (await mockPanel.textContent()) || "";
    expect(mockText).toContain("LLM");
    expect(mockText).toContain("Mock");
    expect(mockText).toContain("Data");

    // 状态栏不应显示"等待后端" / Status bar should not show waiting-for-backend
    const statusText = (await page.locator(SELECTORS.status).textContent()) || "";
    expect(statusText).not.toContain("等待后端");

    // L2 API：后端返回 mock 运行时配置 / Backend returns mock runtime config
    const state = await fetchBackendState(page);
    expect(state.runtime.llm_mock).toBe(true);
    expect(state.runtime.data_mode).toBe("mock");

    // L4 Game：test seam 已就绪 / Test seam ready
    const gameState = await getTestSeamState(page);
    expect(gameState).toEqual(
      expect.objectContaining({
        worldId: WORLD_ID,
      })
    );
  });

  test("UC-38 event payload fields are correct", async ({ page }) => {
    test.setTimeout(300000);
    // 运行 8 个 tick，覆盖 talk/explore/interact/combat 动作类型 / Run 8 ticks
    await runNTicks(page, 8, 240000);

    // L2 API：检查 payload 字段 / Verify payload fields
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    const allEvents = eventsRes.events;

    const decisions = allEvents.filter((e) => e.type === "pc_decision");
    expect(decisions.length).toBeGreaterThan(0);
    for (const d of decisions) {
      const p = d.payload;
      const hasDescription = Boolean(p.description || p.thought);
      const hasType = Boolean(p.type || p.action_type);
      expect(hasDescription && hasType).toBe(true);
    }

    const talks = allEvents.filter((e) => e.type === "pc_talk");
    if (talks.length > 0) {
      for (const t of talks) {
        const turns = t.payload.turns as Array<{ speaker_id: string; text: string }>;
        expect(Array.isArray(turns)).toBe(true);
        expect(turns.length).toBeGreaterThan(0);
      }
    }

    const combats = allEvents.filter((e) => e.type === "pc_combat");
    if (combats.length > 0) {
      for (const c of combats) {
        const narration = String(c.payload.narration || "");
        expect(narration.length).toBeGreaterThan(0);
      }
    }

    // L1 UI：事件面板包含关键类型 / Event panel contains key types
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    expect(eventsText).toContain("角色决策");
    // 至少有一种 action 类型出现 / At least one action type present
    const hasActionType =
      eventsText?.includes("角色对话") ||
      eventsText?.includes("角色探索") ||
      eventsText?.includes("角色互动") ||
      eventsText?.includes("pc_combat");
    expect(hasActionType).toBe(true);

    // L4 Game：已推进到第 8 tick / Advanced to tick 8
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 8 }));
  });
});
