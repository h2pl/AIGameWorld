/** 入口选择页 / Entry Screen — 列出可选世界，用户选择后进入主画面 */
import { CONFIG } from "./config";
import { fetchWorlds } from "./client/api";
import { createLogger } from "./utils/logger";
const log = createLogger("EntryScreen");

/**
 * 渲染世界选择页并等待用户选择 / Render world selection screen and await user choice.
 *
 * 选择后通过 location.search 追加 ?world=<id> 并 reload，主流程用 world id 查询进入。
 * 返回 Promise<boolean>：true=用户已选择（页面将 reload）；false=当前 URL 已有 world，无需选择。
 */
export async function showWorldSelectionIfNeeded(): Promise<boolean> {
  const params = new URLSearchParams(window.location.search);
  // 已有 world 参数 → 直接进入，无需选择 / Already has world → skip selection
  if (params.get("world")) return false;

  // 拉取世界列表 / Fetch world list
  let worlds: any[] = [];
  try {
    worlds = await fetchWorlds(CONFIG.API.base);
    log.info(`loaded ${worlds.length} worlds for selection`);
  } catch (e) {
    log.warn(`failed to load worlds for selection`, e);
  }

  // 渲染全屏选择覆盖层 / Render fullscreen selection overlay
  const overlay = document.createElement("div");
  overlay.id = "entry-screen";
  overlay.style.cssText =
    "position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;" +
    "background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:#e0e0e0;" +
    "z-index:99999;font-family:Segoe UI,sans-serif;overflow-y:auto;";
  overlay.innerHTML = `
    <div style="text-align:center;margin-bottom:24px;">
      <div style="font-size:42px;color:#ffd700;font-weight:bold;margin-bottom:8px;">AIGameWorld</div>
      <div style="font-size:16px;color:#8899aa;">选择一个世界进入 / Select a world to enter</div>
    </div>
    <div id="entry-world-list" style="display:flex;flex-wrap:wrap;gap:16px;justify-content:center;max-width:960px;padding:0 20px;"></div>
    <div id="entry-loading" style="color:#ffd700;margin-top:20px;">加载世界中...</div>
  `;
  document.body.appendChild(overlay);

  const listEl = overlay.querySelector("#entry-world-list") as HTMLElement;
  const loadingEl = overlay.querySelector("#entry-loading") as HTMLElement;

  if (!worlds.length) {
    loadingEl.textContent = "暂无可用世界，请先在后端导入 world pack";
    // 提供默认 mock_world 入口 / Provide default mock entry
    const fallback = _card("mock_world", "Mock World", "默认演示世界（未导入 world 时的回退）");
    listEl.appendChild(fallback);
    return _awaitChoice();
  }

  loadingEl.style.display = "none";
  for (const w of worlds) {
    listEl.appendChild(_card(w.id, w.name, w.description));
  }
  return _awaitChoice();
}

/** 创建世界选择卡片 / Build a world selection card */
function _card(worldId: string, name: string, desc: string): HTMLElement {
  const card = document.createElement("div");
  card.className = "entry-card";
  card.style.cssText =
    "background:rgba(255,255,255,0.06);border:1px solid rgba(255,215,0,0.25);" +
    "border-radius:10px;padding:20px;width:260px;cursor:pointer;" +
    "transition:transform .15s, border-color .15s, background .15s;";
  card.innerHTML = `
    <div style="font-size:18px;color:#ffd700;font-weight:bold;margin-bottom:8px;">${_esc(name)}</div>
    <div style="font-size:13px;color:#8899aa;min-height:36px;">${_esc(desc || "")}</div>
    <div style="margin-top:12px;font-size:12px;color:#4a90d9;">进入 →</div>
  `;
  card.onmouseenter = () => {
    card.style.transform = "scale(1.03)";
    card.style.borderColor = "#ffd700";
    card.style.background = "rgba(255,215,0,0.1)";
  };
  card.onmouseleave = () => {
    card.style.transform = "scale(1)";
    card.style.borderColor = "rgba(255,215,0,0.25)";
    card.style.background = "rgba(255,255,255,0.06)";
  };
  card.onclick = () => {
    // 追加 ?world=<id> 并 reload，主流程用 world id 查询进入 / Append ?world=<id> and reload
    const url = new URL(window.location.href);
    url.searchParams.set("world", worldId);
    window.location.href = url.toString();
  };
  return card;
}

/** 等待用户选择（阻塞），点击卡片后页面 reload，此 Promise 实际不会 resolve / Await user choice (blocks); page reloads on click */
function _awaitChoice(): Promise<boolean> {
  return new Promise(() => {
    // 永不 resolve——用户点击卡片会触发页面 reload / Never resolve—clicking a card reloads the page
  });
}

/** HTML 转义 / HTML escape */
function _esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
