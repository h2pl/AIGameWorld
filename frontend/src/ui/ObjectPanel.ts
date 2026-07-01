/** 场景物品面板 / Scene Object Panel — 点击宝箱/门/地标弹出信息，ESC/✕ 关闭
 *
 * Reldens 模式：不需要 click-outside 关闭，只用 ✕ + ESC（避免竞态）
 * 和 CharacterPanel 共享同一个 .panel 样式体系
 */
import { Panel } from "./Panel";
import type { SceneObjectData } from "../types";

/** 物品类型 → 图标+中文映射 / Object type → icon mapping */
const OBJ_TYPES: Record<string, string> = {
  container: "📦 宝箱 / Chest",
  door: "🚪 门 / Door",
  landmark: "📍 地标 / Landmark",
};

export class ObjectPanel extends Panel {
  /** 内容区 DOM 引用 / Content area reference */
  private contentEl!: HTMLElement;

  constructor() {
    super("object-panel");
  }

  /** 构建面板 HTML / Build panel HTML */
  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel object-panel";
    el.style.display = "none"; // 默认隐藏 / Hidden by default
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">📦</span>
        <span class="panel-title">物品 / Object</span>
        <button class="panel-close" title="关闭 / Close">✕</button>
      </div>
      <div class="panel-body object-body"></div>
    `;
    this.contentEl = el.querySelector(".object-body")!;
    return el;
  }

  /** 绑定事件：关闭按钮 + ESC 键 + object-interacted 监听 / Bind events */
  protected bindEvents(): void {
    this.el.querySelector(".panel-close")?.addEventListener("click", (e) => {
      e.stopPropagation(); this.hide();
    });
    document.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Escape" && this.el.style.display !== "none") this.hide();
    });
    document.addEventListener("object-interacted", ((e: CustomEvent) => {
      this.showObj(e.detail); // GameScene 点击物品时派发
    }) as EventListener);
  }

  /** 展示物品信息 / Show object info
   * TODO: 接入后端后，物品交互数据（描述/内容/触发效果）由 object-interacted 的 detail 字段携带
   */
  private showObj(obj: SceneObjectData): void {
    this.contentEl.innerHTML = `
      <div class="char-name">${OBJ_TYPES[obj.object_type] || obj.object_type} — ${obj.name}</div>
      <div class="char-meta">场景: ${obj.scene_id}　|　位置: (${obj.position_x}, ${obj.position_y})</div>
      <div class="section">
        <div class="section-title">📋 类型 / Type</div>
        <p>${obj.object_type} — 交互功能待开发 / Interaction TBD</p>
        <!-- TODO: 后端稳定后，物品交互数据（描述/内容/触发效果）由 object-interacted event detail 携带 -->
      </div>
    `;
    this.show(); // Panel.show() 设置 display:block
  }
}
