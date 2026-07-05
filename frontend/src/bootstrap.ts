/** 启动引导 / Bootstrap — 等后端就绪 + 加载世界状态 */
import { CONFIG } from "./config";
import type { InitialWorldState } from "./types";

const L = "[Bootstrap]";

/** 等待后端健康检查通过 / Wait until backend health check passes */
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
        console.log(`${L} backend ready after ${attempt} attempt(s)`);
        return true;
      }
      console.warn(`${L} backend health not ok (${resp.status}), attempt ${attempt}`);
    } catch {
      console.warn(`${L} backend not reachable, attempt ${attempt}`);
    }
    if (statusEl) statusEl.textContent = `等待后端就绪... (${attempt})`;
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
  console.error(`${L} backend readiness timeout after ${timeoutMs}ms`);
  return false;
}

/** 从后端加载初始世界状态 / Load initial world state from backend */
export async function loadWorldState(packId: string): Promise<InitialWorldState | null> {
  const url = `${CONFIG.API.base}${CONFIG.API.worldState}/${packId}/state`;
  console.log(`${L} loadWorldState: fetching ${url}`);
  const maxAttempts = 5;
  const delayMs = 500;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const resp = await fetch(url);
      if (resp.ok) {
        const data = (await resp.json()) as InitialWorldState;
        console.log(`${L} API OK: pack=${data.world_id} chars=${data.characters?.length || 0}`);
        return data;
      }
      console.warn(`${L} API not available (${resp.status}), attempt ${attempt}/${maxAttempts}`);
    } catch (e) {
      console.warn(
        `${L} Backend unreachable, attempt ${attempt}/${maxAttempts}`,
        e instanceof Error ? e.message : e
      );
    }
    if (attempt < maxAttempts) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
  console.error(`${L} backend unreachable after retries, using mock`);
  return null;
}

/** 完整启动引导：等后端 → 加载世界 / Full bootstrap: wait for backend → load world */
export async function bootstrap(): Promise<{
  world: InitialWorldState;
  packId: string;
}> {
  // 等待遮罩 / Wait overlay
  const waitOverlay = document.createElement("div");
  waitOverlay.id = "backend-wait-overlay";
  waitOverlay.style.cssText =
    "position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#1a1a2e;color:#ffd700;z-index:9999;font-size:18px;font-family:Segoe UI,sans-serif;";
  waitOverlay.textContent = "等待后端就绪...";
  document.body.appendChild(waitOverlay);
  const backendReady = await waitForBackend(waitOverlay);
  waitOverlay.remove();

  const params = new URLSearchParams(window.location.search);
  const packId = params.get("pack") || "mock_world";
  console.log(`${L} world_id=${packId}`);

  let world: InitialWorldState | null = null;
  if (backendReady) {
    world = await loadWorldState(packId);
  }
  if (!world) {
    world = {
      world_id: packId,
      data_tick: 0,
      display_tick: 0,
      llm_mock: false,
      data_mode: "unknown",
      db_name: "unknown",
      runtime: { llm_mock: false, data_mode: "unknown", db_name: "unknown" },
      scenes: [],
      characters: [],
      items: [],
      scene_objects: [],
    };
  }
  return { world, packId };
}
