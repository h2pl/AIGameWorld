/** Playwright E2E 配置 / Playwright E2E configuration.
 *
 * 启动顺序：
 * 1. globalSetup 启动后端（mock LLM + 独立 DB）
 * 2. webServer 启动前端 Vite dev server
 * 3. 测试用 Chromium 访问 http://localhost:5173
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  timeout: 180000,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // 前后端共享一个世界，串行避免冲突
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  globalSetup: "./tests/e2e/global-setup.ts",
  globalTeardown: "./tests/e2e/global-teardown.ts",
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
