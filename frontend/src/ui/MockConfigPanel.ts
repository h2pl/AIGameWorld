/** Mock 配置面板 / Mock config panel — 显示 LLM/Data/DB 状态 */
import { Panel } from "./Panel";
import { worldStore } from "../state/WorldStore";

export class MockConfigPanel extends Panel {
  constructor() {
    super("mock-config-panel");
  }

  protected buildDOM(): HTMLElement {
    const rt = worldStore.getState().runtime;
    const el = document.createElement("div");
    el.className = "panel mock-config-panel";
    el.innerHTML = [
      `<div class="mock-config-row"><span class="mock-config-label">LLM</span><span class="mock-config-value">${rt.llm_mock ? "Mock" : "Real"}</span></div>`,
      `<div class="mock-config-row"><span class="mock-config-label">Data</span><span class="mock-config-value">${rt.data_mode === "mock" ? "Mock" : rt.data_mode}</span></div>`,
      `<div class="mock-config-row"><span class="mock-config-label">DB</span><span class="mock-config-value">${rt.db_name || "--"}</span></div>`,
    ].join("");
    return el;
  }
}
