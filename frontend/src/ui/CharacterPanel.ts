/** 角色信息面板 / Character Info Panel — 点击角色展示属性 + 战斗 + 角色弧 */
import { Panel } from "./Panel";
import type { CharacterArcData, CharacterData } from "../types";

const ATTR_LABELS: Record<string, string> = {
  strength: "💪 力量",
  dexterity: "🤸 敏捷",
  constitution: "❤️ 体质",
  intelligence: "🧠 智力",
  wisdom: "🧘 感知",
  charisma: "👑 魅力",
};

export class CharacterPanel extends Panel {
  private contentEl!: HTMLElement;

  constructor() {
    super("character-panel");
  }

  protected buildDOM(): HTMLElement {
    const el = document.createElement("div");
    el.className = "panel character-panel";
    el.style.display = "none"; // 默认隐藏 / Hidden by default
    el.innerHTML = `
      <div class="panel-header">
        <span class="panel-icon">🧑</span>
        <span class="panel-title">角色 / Character</span>
        <button class="panel-close" title="关闭 / Close">✕</button>
      </div>
      <div class="panel-body character-body"></div>
    `;
    this.contentEl = el.querySelector(".character-body")!;
    return el;
  }

  protected bindEvents(): void {
    // 关闭按钮 / Close button
    this.el.querySelector(".panel-close")?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.hide();
    });
    // ESC 关闭（Reldens/SkyOffice 标准模式）/ ESC to close
    document.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Escape" && this.el.style.display !== "none") this.hide();
    });
    // 监听角色选择事件 / Listen to character-selected event
    document.addEventListener("character-selected", ((e: CustomEvent) => {
      this.showChar(e.detail);
    }) as EventListener);
  }

  private showChar(ch: CharacterData): void {
    const attrRows = Object.entries(ch.attributes || {})
      .map(([k, v]) => `<span class="attr"><b>${ATTR_LABELS[k] || k}</b> ${v}</span>`)
      .join(" ");

    const combatHtml = ch.combat
      ? `
        <div class="section combat-section">
          <div class="section-title">⚔️ 战斗 / Combat</div>
          <div class="hp-bar-wrap">
            <div class="hp-bar-fill" style="width:${Math.max((ch.combat.hp / ch.combat.max_hp) * 100, 0)}%"></div>
          </div>
          <span class="combat-stat">❤️ HP ${ch.combat.hp}/${ch.combat.max_hp}</span>
          <span class="combat-stat">🛡️ AC ${ch.combat.ac}</span>
          <span class="combat-stat">⚔️ 攻击 +${ch.combat.attack_bonus} (${ch.combat.damage_dice})</span>
          <span class="combat-stat">⚡ 先攻 ${ch.combat.initiative}</span>
        </div>`
      : `<div class="section">⚔️ 无战斗数据 / No combat data</div>`;

    // 角色弧：兼容字符串或 {stage,description} 对象 / Arc: string or {stage,description}
    let arcText = "";
    if (ch.character_arc) {
      if (typeof ch.character_arc === "string") arcText = ch.character_arc as unknown as string;
      else {
        const arcObj = ch.character_arc as CharacterArcData;
        arcText = `[${arcObj.stage || ""}] ${arcObj.description || ""}`.trim();
      }
    }
    const arcHtml = arcText
      ? `<div class="section">
           <div class="section-title">📖 角色弧 / Arc</div>
           ${arcText}
         </div>`
      : "";

    // 背景信息 / Background info (PC)
    const bgHtml = ch.is_pc
      ? `
      ${ch.long_term_goal ? `<div class="section"><div class="section-title">🎯 长期目标 / Goal</div>${ch.long_term_goal}</div>` : ""}
      ${ch.core_values?.length ? `<div class="section"><div class="section-title">💎 价值观 / Values</div>${ch.core_values.join("、")}</div>` : ""}
      ${
        Object.keys(ch.relationships || {}).length
          ? `<div class="section"><div class="section-title">🤝 人际关系 / Relationships</div>${Object.entries(
              ch.relationships || {}
            )
              .map(([k, v]) => `${k}：${v}`)
              .join("、")}</div>`
          : ""
      }
      ${
        Object.keys(ch.equipment || {}).length
          ? `<div class="section"><div class="section-title">🛡️ 装备 / Equipment</div>${Object.entries(
              ch.equipment || {}
            )
              .map(([k, v]) => `${k}: ${v}`)
              .join("、")}</div>`
          : ""
      }
      ${ch.inventory?.length ? `<div class="section"><div class="section-title">🎒 物品 / Inventory</div>${ch.inventory.map((i) => `${i.item} ×${i.qty}`).join("、")}</div>` : ""}`
      : "";

    this.contentEl.innerHTML = `
      <div class="char-name">${ch.is_pc ? "🟡" : "⚪"} ${ch.name} (${ch.role})</div>
      <div class="char-meta">种族: ${ch.race || "未知"}　|　性格: ${ch.personality || "—"}${ch.disposition ? `　|　立场: ${ch.disposition}` : ""}</div>
      ${bgHtml}
      <div class="section">
        <div class="section-title">📊 属性 / Attributes</div>
        <div class="attr-row">${attrRows}</div>
      </div>
      ${combatHtml}
      ${arcHtml}
    `;

    this.show();
  }
}
