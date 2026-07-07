/** 决策事件处理器 / Decision event handler — 显示 PC 思考过程与决策，角色不移动 */
import { createLogger } from "../../utils/logger";
const log = createLogger("DecisionHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { EventData } from "../../types";

export class DecisionHandler {
  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private followSprite: (sprite: any) => void
  ) {}

  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;

    const pcId = String(payload.pc_id || "");
    const thought = String(payload.thought || "").trim();
    const actionType = String(payload.action_type || "wait");
    const targetId = payload.target_id ? String(payload.target_id) : "";

    log.info(`decision pc=${pcId} action=${actionType} target=${targetId}`);

    const sprite = this.getSprite(pcId);
    if (!sprite) {
      log.warn(`[DecisionHandler] sprite not found: ${pcId}`);
      return;
    }

    // 镜头聚焦思考者 / Camera focuses on thinker
    this.followSprite(sprite.rawSprite);

    // 只展示 thought + 决定摘要 / Show thought + decision summary only
    const decisionLine = `决定：${this._actionLabel(actionType)}${targetId ? " " + targetId : ""}`;
    const text = thought ? `${thought}\n${decisionLine}` : decisionLine;

    // 显示思考泡泡，泡泡关闭后 resolve / Show thought bubble and resolve on close
    return new Promise<void>((resolve) => {
      sprite.think(text, () => resolve());
    });
  }

  private _actionLabel(actionType: string): string {
    const map: Record<string, string> = {
      talk: "交谈",
      interact: "交互",
      combat: "战斗",
      explore: "探索",
      wait: "等待",
    };
    return map[actionType] || actionType;
  }
}
