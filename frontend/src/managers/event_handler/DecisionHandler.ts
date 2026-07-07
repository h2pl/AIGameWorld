/** 决策事件处理器 / Decision event handler — 显示 PC 思考过程与决策 */
import { createLogger } from "../../utils/logger";
const log = createLogger("DecisionHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { EventData } from "../../types";
import { actionLabel } from "../../utils/actionLabel";

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
    const targetId = payload.target_id ? String(payload.target_id) : undefined;
    // explore 目标坐标 / Explore target coordinates
    const ex = payload.explore_x !== undefined ? Number(payload.explore_x) : undefined;
    const ey = payload.explore_y !== undefined ? Number(payload.explore_y) : undefined;
    const explorePos = ex !== undefined && ey !== undefined ? { x: ex, y: ey } : undefined;

    log.info(`decision pc=${pcId} action=${actionType} target=${targetId || ""}`);

    const sprite = this.getSprite(pcId);
    if (!sprite) {
      log.warn(`[DecisionHandler] sprite not found: ${pcId}`);
      return;
    }

    // 镜头聚焦思考者 / Camera focuses on thinker
    this.followSprite(sprite.rawSprite);

    // 语义自然的决策文案 / Natural decision text
    const decisionLine = `决定：${actionLabel(actionType, targetId, explorePos)}`;
    const text = thought ? `${thought}\n${decisionLine}` : decisionLine;

    return new Promise<void>((resolve) => {
      sprite.think(text, () => resolve());
    });
  }
}
