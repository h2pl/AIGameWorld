// --- / ---
// -- file start -- / file start
/** 启动引导 / Bootstrap — 等后端就绪 + 加载世界状态 */
import { CONFIG } from "./config";
import type { InitialWorldState } from "./types";
import { createLogger } from "./utils/logger";
const log = createLogger("Bootstrap");

/** 轮询后端健康检查 / Poll backend health until ready */
export async function waitForBackend(
  statusEl?: HTMLElement,
  pollMs = 800,
  timeoutMs = 60000
): Promise<boolean> {
  const url = `${CONFIG.API.base}${CONFIG.API.health}`;
  const start = Date.now();
  let attempt = 0;
  while (Date.now() - start < timeoutMs) {
    attempt++;
    try {
      const resp = await fetch(url);
      if (resp.ok) {
        log.info(`backend ready after ${attempt} attempt(s)`);
        return true;
      }
      log.warn(`backend health not ok (${resp.status}), attempt ${attempt}`);
    } catch {
      log.warn(`backend not reachable, attempt ${attempt}`);
    }
    if (statusEl) statusEl.textContent = `等待后端就绪... (${attempt})`;
    await new Promise((r) => setTimeout(r, pollMs));
  }
  log.error(`backend readiness timeout after ${timeoutMs}ms`);
  return false;
}

/** 从后端加载世界状态 / Load world state from backend */
export async function loadWorldState(worldId: string): Promise<InitialWorldState | null> {
  const url = `${CONFIG.API.base}${CONFIG.API.worldState}/${worldId}/state`;
  log.info(`loading world: ${url}`);
  for (let i = 1; i <= 5; i++) {
    try {
      const resp = await fetch(url);
      if (resp.ok) {
        const data = (await resp.json()) as InitialWorldState;
        log.info(`world loaded: id=${data.world_id} scenes=${data.scenes?.length || 0}`);
        return data;
      }
      log.warn(`API not available (${resp.status}), attempt ${i}/5`);
    } catch {
      log.warn(`unreachable, attempt ${i}/5`);
    }
    if (i < 5) await new Promise((r) => setTimeout(r, 500));
  }
  log.error(`world load failed`);
  return null;
}

/** 完整启动流程：等后端 → 读世界 → 失败时返回占位数据 / Full bootstrap: wait backend → load world → fallback on failure */
export async function bootstrap(): Promise<{ world: InitialWorldState }> {
  // 显示等待遮罩 / Show loading overlay
  const overlay = document.createElement("div");
  overlay.id = "backend-wait-overlay";
  overlay.style.cssText =
    "position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#1a1a2e;color:#ffd700;z-index:9999;font-size:18px;font-family:Segoe UI,sans-serif;";
  overlay.textContent = "等待后端就绪...";
  document.body.appendChild(overlay);
  const ok = await waitForBackend(overlay);
  overlay.remove();

  const params = new URLSearchParams(window.location.search);
  const worldId = params.get("pack") || "mock_world";

  // 读取 URL 参数 / Read URL pack param
  let world: InitialWorldState | null = null;
  if (ok) world = await loadWorldState(worldId);
  // 后端不可用时的降级数据 / Fallback world when backend is unavailable
  if (!world) {
    world = {
      world_id: worldId,
      data_tick: 0,
      display_tick: 0,
      llm_mock: false,
      data_mode: "unknown",
      db_name: "unknown",
      runtime: { llm_mock: false, data_mode: "unknown", db_name: "unknown" },
      scenes: [],
    };
  }
  return { world };
}
