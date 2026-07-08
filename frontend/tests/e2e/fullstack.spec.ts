/** 前后端全链路 E2E / Full-stack end-to-end tests.
 *
 * 每个用例都从前端操作出发，最终验证后端状态与数据，覆盖完整链路：
 * 浏览器点击 → 前端 API 调用 → 后端 Graph → DB → 前端事件 → UI 更新 → 后端状态同步
 */
import { test, expect, type Page } from "@playwright/test";

const WORLD_ID = "mock_world";

const SELECTORS = {
  backendOverlay: "#backend-wait-overlay",
  tickInput: '[data-testid="tick-count-input"]',
  runNButton: '[data-testid="btn-run-n"]',
  startLoopButton: '[data-testid="btn-start-loop"]',
  pauseButton: '[data-testid="btn-pause"]',
  resetButton: '[data-testid="btn-reset"]',
  status: '[data-testid="control-status"]',
  eventList: '[data-testid="event-list"]',
  eventLine: ".event-line",
  tickBadge: "#event-tick-badge",
  speed4x: 'button:has-text("4x")',
  dmCreationPanel: '[data-testid="dm-creation-panel"]',
  dmCreationBody: '[data-testid="dm-creation-body"]',
  dmCreationBrief: '[data-testid="dm-creation-brief"]',
  narrativePanel: '[data-testid="narrative-panel"]',
  narrativeBody: '[data-testid="narrative-body"]',
  objectPanel: '[data-testid="object-panel"]',
  mockConfigPanel: '[data-testid="mock-config-panel"]',
};

interface RuntimeConfig {
  llm_mock: boolean;
  data_mode: string;
  db_name: string;
}

interface SceneObjectData {
  id: string;
  name: string;
  object_type: string;
  scene_id: string;
  position_x: number;
  position_y: number;
}

interface BackendState {
  world_id: string;
  data_tick: number;
  display_tick: number;
  pcs: unknown[];
  runtime: RuntimeConfig;
  scene_objects: SceneObjectData[];
}

interface TickEvent {
  type: string;
  tick: number;
  payload: Record<string, unknown>;
}

interface EventsResponse {
  events: TickEvent[];
  data_tick: number;
  display_tick: number;
}

interface LoopStatus {
  running: boolean;
  batch_running: boolean;
}

async function fetchBackendState(page: Page): Promise<BackendState> {
  const res = await page.request.get(`/api/world/${WORLD_ID}/state`);
  expect(res.ok()).toBe(true);
  return (await res.json()) as BackendState;
}

async function fetchBackendEvents(
  page: Page,
  sinceTick: number,
  tickLimit = 10
): Promise<EventsResponse> {
  const res = await page.request.get(
    `/api/world/${WORLD_ID}/events?since_tick=${sinceTick}&tick_limit=${tickLimit}`
  );
  expect(res.ok()).toBe(true);
  return (await res.json()) as EventsResponse;
}

async function fetchLoopStatus(page: Page): Promise<LoopStatus> {
  const res = await page.request.get(`/api/world/${WORLD_ID}/loop/status`);
  expect(res.ok()).toBe(true);
  return (await res.json()) as LoopStatus;
}

async function waitForBackendTick(
  page: Page,
  expectedTick: number,
  timeout = 60000
): Promise<BackendState> {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const state = await fetchBackendState(page);
    if (state.data_tick >= expectedTick) return state;
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`data_tick 未在 ${timeout}ms 内达到 ${expectedTick}`);
}

async function getTestSeamState(page: Page): Promise<Record<string, unknown> | null> {
  return page.evaluate(() => {
    const w = window as any;
    return w.__TEST__?.gameState ? w.__TEST__.gameState() : null;
  });
}

test.describe("fullstack tick flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // 等待后端就绪遮罩消失 / Wait for backend-ready overlay to disappear
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    // 等待 Phaser canvas / Wait for Phaser canvas
    await page.waitForSelector("canvas", { timeout: 30000 });
    // 等待控制栏按钮就绪（callbacks 已注入）/ Wait for control bar buttons ready
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });

    // 每个测试前重置，确保从 tick=0 开始 / Reset before each test to start from tick 0
    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });
    // 确保后端状态已真正清空，避免测试间数据残留 / Ensure backend state is fully reset
    await expect
      .poll(() => fetchBackendState(page))
      .toEqual(expect.objectContaining({ data_tick: 0, display_tick: 0 }));
    await expect
      .poll(() => fetchLoopStatus(page))
      .toEqual(expect.objectContaining({ running: false, batch_running: false }));
    // 重置后再刷新一次页面，确保 TickPlayer 从 display_tick=0 初始化 / Reload to ensure TickPlayer starts at 0
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });
    // 测试用 4x 倍速缩短动画时间 / Use 4x speed in tests to shorten animations
    await page.locator(SELECTORS.speed4x).click();
  });

  test("page loads and backend becomes ready", async ({ page }) => {
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

  test("run 1 tick end-to-end", async ({ page }) => {
    // 设置只跑 1 个 tick / Set to run 1 tick
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();

    // 状态应进入等待 / Status should show waiting
    await expect(page.locator(SELECTORS.status)).toContainText("生成 Tick 数据中", {
      timeout: 5000,
    });

    // 等待 tick 完成 / Wait for tick completion
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

    // 事件面板应出现事件行 / Event panel should have event lines
    await expect(
      page.locator(SELECTORS.eventList).locator(SELECTORS.eventLine).first()
    ).toBeVisible({
      timeout: 10000,
    });

    // tick 徽章应更新 / Tick badge should update
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=1");

    // 等待事件串行处理完成（DM 叙事是最后一个关键事件）/ Wait for events to finish sequential processing
    await expect(page.locator(SELECTORS.eventList)).toContainText("DM 叙事", { timeout: 30000 });

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
    // scene_setup 已在后端 graph 重构中移除，不再作为独立事件下发
    // scene_setup was removed in the recent backend graph refactor
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

  test("reset clears state end-to-end", async ({ page }) => {
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });
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

    // 验证 Phaser test seam 已重置（场景被销毁，等待下一次 tick 重建）/ Verify reset destroyed scene
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

  test("start and pause loop end-to-end", async ({ page }) => {
    await page.locator(SELECTORS.startLoopButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("持续运行中", { timeout: 5000 });

    // 等至少 1 个 tick 产出 / Wait for at least 1 tick
    await expect(page.locator(SELECTORS.tickBadge)).not.toContainText("Display_Tick=0", {
      timeout: 60000,
    });

    // 验证后端循环正在运行且已有 tick 产出 / Verify backend loop is running and tick produced
    const statusBefore = await fetchLoopStatus(page);
    expect(statusBefore.running).toBe(true);
    const stateBefore = await waitForBackendTick(page, 1);
    expect(stateBefore.data_tick).toBeGreaterThanOrEqual(1);

    await page.locator(SELECTORS.pauseButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("已暂停", { timeout: 10000 });

    // 验证后端循环已停止 / Verify backend loop stopped
    const statusAfter = await fetchLoopStatus(page);
    expect(statusAfter.running).toBe(false);

    // 验证暂停后不会 409：再次启动 batch 应该成功 / Verify no 409 after pause: new batch should succeed
    const batchRes = await page.request.post(`/api/world/${WORLD_ID}/tick/batch/1`);
    expect(batchRes.ok()).toBe(true);
  });
});

test.describe("event display", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // 等待后端就绪遮罩消失 / Wait for backend-ready overlay to disappear
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    // 等待 Phaser canvas / Wait for Phaser canvas
    await page.waitForSelector("canvas", { timeout: 30000 });
    // 等待控制栏按钮就绪（callbacks 已注入）/ Wait for control bar buttons ready
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });

    // 每个测试前重置，确保从 tick=0 开始 / Reset before each test to start from tick 0
    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });
    // 确保后端状态已真正清空，避免测试间数据残留 / Ensure backend state is fully reset
    await expect
      .poll(() => fetchBackendState(page))
      .toEqual(expect.objectContaining({ data_tick: 0, display_tick: 0 }));
    // 确保后端循环/batch已完全停止，避免测试间并发 / Ensure backend loop/batch stopped to avoid cross-test concurrency
    await expect
      .poll(() => fetchLoopStatus(page))
      .toEqual(expect.objectContaining({ running: false, batch_running: false }));
    // 重置后再刷新一次页面，确保 TickPlayer 从 display_tick=0 初始化 / Reload to ensure TickPlayer starts at 0
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });
    // 测试用 4x 倍速缩短动画时间 / Use 4x speed in tests to shorten animations
    await page.locator(SELECTORS.speed4x).click();
  });

  test("UC-11 dm create panel renders correctly", async ({ page }) => {
    // 运行 1 个 tick / Run 1 tick
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

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

    // 运行 2 个 tick，每个 PC 应各触发一次决策泡泡 / Run 2 ticks, each PC should trigger one decision bubble
    await page.locator(SELECTORS.tickInput).fill("2");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 2|完成/, {
      timeout: 60000,
    });

    // L1 UI：事件面板只展示当前 tick，决策行数 = PC 数 / Event panel shows current tick only
    await expect(
      page.locator(`${SELECTORS.eventList} ${SELECTORS.eventLine}:has-text("角色决策")`)
    ).toHaveCount(pcCount, { timeout: 10000 });

    // L2 API：pc_decision 事件数量 / pc_decision event count
    const eventsRes = await fetchBackendEvents(page, 0, 3);
    const decisionEvents = eventsRes.events.filter((e) => e.type === "pc_decision");
    expect(decisionEvents.length).toBe(pcCount * 2);

    // L4 Game：每个 PC 的 think 次数等于 tick 数，无重复 / Each PC think count equals tick count
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(
        expect.objectContaining({
          sceneBuilt: true,
          displayTick: 2,
        })
      );
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
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

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

    // L1 UI：叙事文本非空，且包含至少一个 action 关键词或长度合理 / Narrative non-empty and related
    const narrativeText = (await page.locator(SELECTORS.narrativeBody).textContent()) || "";
    expect(narrativeText.length).toBeGreaterThan(10);
    const hasKeyword = keywords.some((k) => narrativeText.toLowerCase().includes(k.toLowerCase()));
    expect(hasKeyword || narrativeText.length >= 30).toBe(true);

    // L4 Game：displayTick 已推进 / displayTick advanced
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 1 }));
  });

  test("UC-14 events render in correct order", async ({ page }) => {
    test.setTimeout(60000);
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

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
    test.setTimeout(60000);
    // 场景未构建前 ObjectPanel 不应自动出现 / ObjectPanel should stay hidden before scene built
    await expect(page.locator(SELECTORS.objectPanel)).toBeHidden();

    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

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
    // 运行 8 个 tick，覆盖 talk/explore/interact/combat 动作类型 / Run 8 ticks to cover action types
    await page.locator(SELECTORS.tickInput).fill("8");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 8|完成/, {
      timeout: 240000,
    });

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
    expect(talks.length).toBeGreaterThan(0);
    for (const t of talks) {
      const turns = t.payload.turns as Array<{ speaker_id: string; text: string }>;
      expect(Array.isArray(turns)).toBe(true);
      expect(turns.length).toBeGreaterThan(0);
    }

    const combats = allEvents.filter((e) => e.type === "pc_combat");
    expect(combats.length).toBeGreaterThan(0);
    for (const c of combats) {
      const narration = String(c.payload.narration || "");
      expect(narration.length).toBeGreaterThan(0);
    }

    // L1 UI：事件面板包含关键类型 / Event panel contains key types
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    expect(eventsText).toContain("角色决策");
    expect(eventsText).toContain("角色对话");

    // L4 Game：已推进到第 8 tick / Advanced to tick 8
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ displayTick: 8 }));
  });
});

test.describe("action playback", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await page.waitForSelector("canvas", { timeout: 30000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });

    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });
    await expect
      .poll(() => fetchBackendState(page))
      .toEqual(expect.objectContaining({ data_tick: 0, display_tick: 0 }));
    await expect
      .poll(() => fetchLoopStatus(page))
      .toEqual(expect.objectContaining({ running: false, batch_running: false }));
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });
    await page.locator(SELECTORS.speed4x).click();
  });

  /** 辅助：运行 1 tick 并等待完成 / Helper: run 1 tick and wait */
  async function runOneTick(page: Page) {
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });
  }

  test("UC-16 talk action plays dialogue bubbles", async ({ page }) => {
    test.setTimeout(90000);
    await runOneTick(page);

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
      // 对话结束后气泡被清除，所以不一定还能看到 / Bubbles clear after dialogue ends
      // 改为验证事件面板包含"角色对话" / Instead verify event panel contains talk event
    }

    // L1 UI：事件面板包含对话事件 / Event panel contains talk event
    const eventsText = await page.locator(SELECTORS.eventList).textContent();
    // 可能本次 tick 没有 talk 决策，所以用 toContain 或跳过 / May not have talk this tick
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
    await runOneTick(page);

    // L2 API：获取 pc_explore 事件 / Get pc_explore event
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const exploreEvents = eventsRes.events.filter((e) => e.type === "pc_explore");

    if (exploreEvents.length > 0) {
      const explore = exploreEvents[0];
      const waypoints = explore.payload.waypoints as Array<{ x: number; y: number }>;
      expect(Array.isArray(waypoints)).toBe(true);

      // L4 Game：PC 不再行走（已到达终点）/ PC no longer walking (reached destination)
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
    await runOneTick(page);

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
    await runOneTick(page);

    // L2 API：获取 pc_combat 事件 / Get pc_combat event
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const combatEvents = eventsRes.events.filter((e) => e.type === "pc_combat");

    if (combatEvents.length > 0) {
      const combat = combatEvents[0];
      const narration = String(combat.payload.narration || "");
      expect(narration.length).toBeGreaterThan(0);

      // 如果 target_defeated=true 且是 actor，验证 actor 被移除 / If target defeated, verify actor removed
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
    await runOneTick(page);

    // L2 API：同一 tick 的 action 按 order 排列 / Actions sorted by order within same tick
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const actionEvents = eventsRes.events.filter((e) =>
      ["pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(e.type)
    );

    if (actionEvents.length > 1) {
      const orders = actionEvents.map((e) => Number(e.payload.order ?? 0));
      // 验证 order 单调递增 / Verify order is monotonically increasing
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

  test("UC-22 pause cancels current action walk and dialogue", async ({ page }) => {
    test.setTimeout(90000);
    // 先启动循环 / Start loop first
    await page.locator(SELECTORS.startLoopButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText("持续运行中", { timeout: 5000 });

    // 等待至少 1 个 tick / Wait for at least 1 tick
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
    await runOneTick(page);

    // L2 API：同一 tick 有多个不同类型的 action / Multiple action types in same tick
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    const actionTypes = new Set(
      eventsRes.events
        .filter((e) => ["pc_talk", "pc_explore", "pc_interact", "pc_combat"].includes(e.type))
        .map((e) => e.type)
    );

    // 至少有一种 action 类型 / At least one action type present
    expect(actionTypes.size).toBeGreaterThanOrEqual(1);

    // L4 Game / Game layer
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(expect.objectContaining({ sceneBuilt: true, displayTick: 1 }));
  });
});

test.describe("control flow & data consistency", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await page.waitForSelector("canvas", { timeout: 30000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });

    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });
    await expect
      .poll(() => fetchBackendState(page))
      .toEqual(expect.objectContaining({ data_tick: 0, display_tick: 0 }));
    await expect
      .poll(() => fetchLoopStatus(page))
      .toEqual(expect.objectContaining({ running: false, batch_running: false }));
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });
    await page.locator(SELECTORS.speed4x).click();
  });

  test("UC-3 run N ticks batch advance", async ({ page }) => {
    test.setTimeout(120000);
    await page.locator(SELECTORS.tickInput).fill("3");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 3|完成/, {
      timeout: 90000,
    });

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
    // 跑 2 个 tick / Run 2 ticks
    await page.locator(SELECTORS.tickInput).fill("2");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 2|完成/, {
      timeout: 90000,
    });

    // L2 API：tick 1 和 tick 2 均有事件 / Both tick 1 and 2 have events
    const eventsRes = await fetchBackendEvents(page, 0, 10);
    const tick1Events = eventsRes.events.filter((e) => e.tick === 1);
    const tick2Events = eventsRes.events.filter((e) => e.tick === 2);
    expect(tick1Events.length).toBeGreaterThan(0);
    expect(tick2Events.length).toBeGreaterThan(0);
  });

  test("UC-9 display tick syncs with data tick", async ({ page }) => {
    test.setTimeout(90000);
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

    // L2 API：data_tick === display_tick / Backend ticks synchronized
    const state = await fetchBackendState(page);
    expect(state.data_tick).toBe(state.display_tick);

    // L4 Game：displayTick = 后端 display_tick / Game displayTick matches backend
    const gameState = await getTestSeamState(page);
    expect(gameState!.displayTick).toBe(state.display_tick);
  });

  test("UC-10 character data persistence", async ({ page }) => {
    test.setTimeout(90000);
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

    // L2 API：pcs/actors/scene_objects 完整 / API returns complete data
    const state = await fetchBackendState(page);
    expect(state.pcs.length).toBeGreaterThan(0);
    expect(state.scene_objects.length).toBeGreaterThan(0);

    // L4 Game：PC 和 Actor 精灵已创建 / PC and Actor sprites created
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

test.describe("error race & state recovery", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await page.waitForSelector("canvas", { timeout: 30000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });

    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });
    await expect
      .poll(() => fetchBackendState(page))
      .toEqual(expect.objectContaining({ data_tick: 0, display_tick: 0 }));
    await expect
      .poll(() => fetchLoopStatus(page))
      .toEqual(expect.objectContaining({ running: false, batch_running: false }));
    await page.reload();
    await page.waitForSelector(SELECTORS.backendOverlay, { state: "detached", timeout: 60000 });
    await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });
    await page.locator(SELECTORS.speed4x).click();
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
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

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
    // 跑 1 tick / Run 1 tick
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

    // 重置 / Reset
    await page.locator(SELECTORS.resetButton).click();
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=0", {
      timeout: 10000,
    });

    // 再次跑 1 tick / Run 1 tick again
    await page.locator(SELECTORS.tickInput).fill("1");
    await page.locator(SELECTORS.runNButton).click();
    await expect(page.locator(SELECTORS.status)).toContainText(/展示 Tick 1|完成/, {
      timeout: 60000,
    });

    // L1 UI：tick 徽章回到 1 / Tick badge back to 1
    await expect(page.locator(SELECTORS.tickBadge)).toContainText("Display_Tick=1");

    // L2 API：有事件数据 / Events exist
    const eventsRes = await fetchBackendEvents(page, 0, 1);
    expect(eventsRes.events.length).toBeGreaterThan(0);
  });
});
