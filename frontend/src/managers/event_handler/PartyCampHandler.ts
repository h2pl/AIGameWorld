/** 夜晚回营事件处理器 / Party camp event handler — 全员回出生点 + 旁白 */
import { createLogger } from "../../utils/logger";
const log = createLogger("PartyCampHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";
import { speedMs } from "../../config/playback";
import { contentDuration } from "../../utils/contentDuration";

export class PartyCampHandler {
  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getAnySprite: () => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private followSprite: (sprite: any) => void
  ) {}

  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const pcs =
      (payload.pcs as Array<{ pc_id: string; position_x: number; position_y: number }>) || [];
    log.info(`party_camp pcs=${pcs.length} scene=${payload.scene_id}`);

    // 1. 所有 PC 走回出生点（营地）/ walk all PCs back to spawn (camp)
    const mm = this.getMovementManager();
    const walks: Promise<void>[] = [];
    let anySprite: CharacterSprite | undefined;
    for (const p of pcs) {
      const sprite = this.getSprite(p.pc_id);
      if (!sprite) continue;
      anySprite = anySprite || sprite;
      if (mm) {
        walks.push(
          new Promise<void>((resolve) => {
            mm.walkTo(sprite!, p.position_x, p.position_y, { onComplete: () => resolve() });
          })
        );
      }
    }
    // 镜头跟随首个回营成员 / camera follows first camper
    if (anySprite) this.followSprite(anySprite.rawSprite);
    await Promise.all(walks);

    // 2. 播放回营旁白 / play camp narration
    const narration = (payload.narration as string) || "夜幕降临，冒险者们回到营地休整。";
    await new Promise<void>((resolve) => {
      const sprite = this.getAnySprite();
      if (sprite) {
        sprite.showExploreRecord(narration, () => resolve());
      } else {
        setTimeout(resolve, speedMs(contentDuration(narration)));
      }
    });
  }
}
