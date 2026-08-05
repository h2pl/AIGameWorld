// --- / ---
// -- file start -- / file start
/** 启动引导 / Bootstrap — 等后端就绪 + 加载世界状态 */
import { CONFIG } from "./config";
import type { InitialWorldState } from "./types";
import { createLogger } from "./utils/logger";
const log = createLogger("Bootstrap");

/**
 * 后端就绪等待超时 / Backend readiness timeout.
 *
 * 后端启动需加载 BGE-M3 嵌入模型 + 重建 Chroma 集合（首次约 60s），
 * 若前端提前超时降级，会显示 LLM/DB unknown。故超时设 180s，
 * 确保前端真正等后端「完全就绪」后再加载世界状态。
 */
const BACKEND_READY_TIMEOUT_MS = 180_000;

/** 轮询后端健康检查 / Poll backend health until ready */
export async function waitForBackend(
  statusEl?: HTMLElement,
  pollMs = 800,
  timeoutMs = BACKEND_READY_TIMEOUT_MS
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

  // 前端必须等后端「完全就绪」再启动，避免 LLM/DB 显示 unknown。
  // 长时间轮询（不因单次超时降级），直到后端健康检查通过。
  let ok = await waitForBackend(overlay);
  if (!ok) {
    // 后端加载过慢时保持等待，不立即降级为 unknown / Keep waiting, don't degrade to unknown.
    overlay.textContent = "后端仍在启动中，继续等待...";
    log.warn(`first waitForBackend timeout, keep waiting`);
    ok = await waitForBackend(overlay, 1500, 300_000);
  }
  overlay.remove();

  const params = new URLSearchParams(window.location.search);
  // 通过 world id 查询（入口页选择后写入 URL 的 world 参数）/
  // Query by world id (entry page writes world id into URL after selection)
  const worldId = params.get("world") || "mock_world";

  // 读取 URL 参数 / Read URL param
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
