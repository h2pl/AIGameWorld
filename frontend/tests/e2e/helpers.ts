/** E2E 测试公共工具 / Shared E2E test helpers. */
import { expect, type Page } from "@playwright/test";

/** 测试用 world_id / World ID used in all E2E tests */
export const WORLD_ID = "mock_world";

/** UI 选择器常量 / CSS selector constants for E2E test targets */
export const SELECTORS = {
  /** 后端就绪遮罩 / Backend-ready overlay */
  backendOverlay: "#backend-wait-overlay",
  /** tick 数量输入 / Tick count input */
  tickInput: '[data-testid="tick-count-input"]',
  /** 跑 N 个 tick 按钮 / Run N ticks button */
  runNButton: '[data-testid="btn-run-n"]',
  /** 启动循环按钮 / Start loop button */
  startLoopButton: '[data-testid="btn-start-loop"]',
  /** 暂停按钮 / Pause button */
  pauseButton: '[data-testid="btn-pause"]',
  /** 恢复按钮 / Resume button */
  resumeButton: '[data-testid="btn-resume"]',
  /** 重置按钮 / Reset button */
  resetButton: '[data-testid="btn-reset"]',
  /** 控制栏状态文本 / Control bar status text */
  status: '[data-testid="control-status"]',
  /** 事件面板列表 / Event panel list */
  eventList: '[data-testid="event-list"]',
  /** 事件行 / Event line item */
  eventLine: ".event-line",
  /** tick 徽章 / Tick badge */
  tickBadge: "#event-tick-badge",
  /** 4x 倍速按钮 / 4x speed button */
  speed4x: 'button:has-text("4x")',
  /** DM 创建情境面板 / DM creation panel */
  dmCreationPanel: '[data-testid="dm-creation-panel"]',
  /** DM 创建情境正文 / DM creation body */
  dmCreationBody: '[data-testid="dm-creation-body"]',
  /** DM 创建情境摘要 / DM creation brief */
  dmCreationBrief: '[data-testid="dm-creation-brief"]',
  /** 叙事面板 / Narrative panel */
  narrativePanel: '[data-testid="narrative-panel"]',
  /** 叙事正文 / Narrative body */
  narrativeBody: '[data-testid="narrative-body"]',
  /** 场景物体面板 / Scene object panel */
  objectPanel: '[data-testid="object-panel"]',
  /** Mock 配置面板 / Mock config panel */
  mockConfigPanel: '[data-testid="mock-config-panel"]',
};

// ── 类型 / Types ──────────────────────────────────────────────

/** 运行时 Mock 配置 / Runtime mock configuration */
export interface RuntimeConfig {
  llm_mock: boolean;
  data_mode: string;
  db_name: string;
}

/** 场景物体数据 / Scene object data */
export interface SceneObjectData {
  id: string;
  name: string;
  object_type: string;
  scene_id: string;
  position_x: number;
  position_y: number;
}

/** 后端状态响应 / Backend state API response */
export interface BackendState {
  world_id: string;
  data_tick: number;
  display_tick: number;
  pcs: unknown[];
  runtime: RuntimeConfig;
  scene_objects: SceneObjectData[];
}

/** Tick 事件结构 / Tick event structure */
export interface TickEvent {
  type: string;
  tick: number;
  payload: Record<string, unknown>;
}

/** 事件列表响应 / Events list API response */
export interface EventsResponse {
  events: TickEvent[];
  data_tick: number;
  display_tick: number;
}

/** 循环状态 / Loop status API response */
export interface LoopStatus {
  running: boolean;
  batch_running: boolean;
}

// ── API 辅助 / API helpers ───────────────────────────────────

/** 获取后端世界状态 / Fetch backend world state */
export async function fetchBackendState(page: Page): Promise<BackendState> {
  const res = await page.request.get(`/api/world/${WORLD_ID}/state`);
  expect(res.ok()).toBe(true);
  return (await res.json()) as BackendState;
}

/** 获取后端事件列表 / Fetch backend events since given tick */
export async function fetchBackendEvents(
  page: Page,
  sinceTick: number,
  tickLimit = 10
): Promise<EventsResponse> {
  // 重试 3 次避免后端短暂不可用 / Retry to handle transient backend unavailability
  for (let attempt = 0; attempt < 3; attempt++) {
    const res = await page.request.get(
      `/api/world/${WORLD_ID}/events?since_tick=${sinceTick}&tick_limit=${tickLimit}`
    );
    if (res.ok()) return (await res.json()) as EventsResponse;
    if (attempt < 2) await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`fetchBackendEvents failed after 3 attempts`);
}

/** 获取循环运行状态 / Fetch loop running status */
export async function fetchLoopStatus(page: Page): Promise<LoopStatus> {
  const res = await page.request.get(`/api/world/${WORLD_ID}/loop/status`);
  expect(res.ok()).toBe(true);
  return (await res.json()) as LoopStatus;
}

/** 轮询等待后端 data_tick 达到目标 / Poll until backend data_tick reaches target */
export async function waitForBackendTick(
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

// ── Test seam / Game state ────────────────────────────────────

/** 通过 window.__TEST__ 获取 Phaser 游戏状态 / Get Phaser game state via test seam */
export async function getTestSeamState(page: Page): Promise<Record<string, unknown> | null> {
  return page.evaluate(() => {
    const w = window as any;
    return w.__TEST__?.gameState ? w.__TEST__.gameState() : null;
  });
}

// ── beforeEach：重置 + 4x 倍速 / Reset + 4x speed ────────────

/** beforeEach 标准流程：重置 → 刷新 → 1x 倍速（默认速度，避免 headless crash） */
export async function resetAndPrepare(page: Page): Promise<void> {
  await page.goto("/");
  await page.waitForSelector(SELECTORS.backendOverlay, {
    state: "detached",
    timeout: 60000,
  });
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
  await page.waitForSelector(SELECTORS.backendOverlay, {
    state: "detached",
    timeout: 90000,
  });
  await expect(page.locator(SELECTORS.runNButton)).toBeEnabled({ timeout: 10000 });
  // 默认 1x 速度，避免 headless Phaser + scene_setup rebuild 导致的 GPU crash
}

// ── 辅助：运行 N tick 并等待完成 / Run N ticks and wait ─────

/** 运行 N 个 tick 并等待前后端全部完成 / Run N ticks and wait for complete pipeline finish */
export async function runNTicks(page: Page, n: number, timeout = 60000): Promise<void> {
  await page.locator(SELECTORS.tickInput).fill(String(n));
  await page.locator(SELECTORS.runNButton).click();
  // 等后端 data_tick 到达目标（不检查 UI，scene_setup 会改变状态文本）
  await waitForBackendTick(page, n, timeout);
}
