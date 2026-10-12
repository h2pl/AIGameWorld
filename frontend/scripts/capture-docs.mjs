/**
 * README 文档截图生成脚本 / Docs screenshot generator
 *
 * 用法 / Usage:
 *   前置：后端已启动（8001）且 `npm run dev` 已启动（3000）
 *   cd frontend && npm run docs:screens
 *
 * 输出 / Output: docs/images/*.png（供根目录 README.md 引用）
 * 可用环境变量 BASE 覆盖前端地址（默认 http://localhost:3000）。
 */
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.env.BASE || "http://localhost:3000";
const OUT_DIR = path.resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "..",
  "..",
  "docs",
  "images"
);
const WORLD_NAME = process.env.WORLD_NAME || "星槎大陆";
const VIEW = { width: 1920, height: 1080 };

/** 等待真实内容渲染（排除占位符）/ Wait for real content (placeholder excluded) */
async function waitContent(selector, timeout = 120_000) {
  await selector
    .first()
    .waitFor({ state: "visible", timeout })
    .catch(() => console.warn("warn: 等待内容超时，继续截图"));
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: VIEW, deviceScaleFactor: 1.5 });

  // ── 1. 世界选择入口页 ──
  console.log("==> 1/3 世界选择页", BASE);
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.locator(".entry-card").first().waitFor({ timeout: 30_000 });
  await page.waitForTimeout(1_000);
  await page.screenshot({ path: path.join(OUT_DIR, "01-world-select.png") });

  // ── 2. 进入世界，主界面渲染 ──
  console.log(`==> 2/3 进入世界「${WORLD_NAME}」，等待地图与面板就绪`);
  await page.locator(`.entry-card:has-text("${WORLD_NAME}")`).first().click();
  await page.waitForURL(/world=/, { timeout: 30_000 });
  await page.locator("canvas").waitFor({ state: "visible", timeout: 60_000 });
  // DM 情境面板出现实际内容（首轮 LLM 生成可能较慢）
  await waitContent(page.locator('[data-testid="dm-creation-brief"] .dm-creation-line'));
  await page.waitForTimeout(3_000);
  await page.screenshot({ path: path.join(OUT_DIR, "02-game-overview.png") });

  // ── 3. 启动循环跑 tick，事件/叙事产出后截图 ──
  console.log("==> 3/3 启动 tick 循环，等待事件与叙事");
  await page.locator('[data-testid="btn-start-loop"]').click();
  await waitContent(page.locator('[data-testid="narrative-body"] .narrative-line'), 240_000);
  await page.waitForTimeout(5_000);
  await page.screenshot({ path: path.join(OUT_DIR, "03-game-running.png") });

  // ── 面板特写 ──
  const shots = [
    ['[data-testid="dm-creation-panel"]', "04-dm-creation-panel.png"],
    ['[data-testid="narrative-panel"]', "05-narrative-panel.png"],
  ];
  for (const [selector, file] of shots) {
    const el = page.locator(selector).first();
    if (await el.isVisible().catch(() => false)) {
      await el.screenshot({ path: path.join(OUT_DIR, file) });
      console.log("    saved", file);
    } else {
      console.warn("warn: 面板不可见，跳过", selector);
    }
  }
  // 事件面板：容器无 testid，用包含 event-list 的 .panel 定位
  const eventPanel = page
    .locator(".panel")
    .filter({ has: page.locator('[data-testid="event-list"]') })
    .first();
  if (await eventPanel.isVisible().catch(() => false)) {
    await eventPanel.screenshot({ path: path.join(OUT_DIR, "06-events-panel.png") });
    console.log("    saved 06-events-panel.png");
  } else {
    console.warn("warn: 事件面板不可见，跳过");
  }

  await browser.close();
  console.log("done →", OUT_DIR);
}

main().catch((err) => {
  console.error("capture failed:", err);
  process.exit(1);
});
