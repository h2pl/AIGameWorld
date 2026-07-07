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
};

interface BackendState {
  world_id: string;
  data_tick: number;
  display_tick: number;
  pcs: unknown[];
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
          sceneBuilt: true,
          pcCount: state.pcs.length,
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

    // 验证 Phaser test seam 已重置并重建场景 / Verify reset and scene rebuilt
    await expect
      .poll(() => getTestSeamState(page))
      .toEqual(
        expect.objectContaining({
          sceneBuilt: true,
          pcCount: stateAfter.pcs.length,
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
