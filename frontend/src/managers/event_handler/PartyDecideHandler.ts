/** 集体决策事件处理器 / Party decision event handler — 场景切换裁决旁白 */
import { createLogger } from "../../utils/logger";
const log = createLogger("PartyDecideHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { EventData } from "../../types";
import { speedMs } from "../../config/playback";
import { contentDuration } from "../../utils/contentDuration";

export class PartyDecideHandler {
  constructor(private getAnySprite: () => CharacterSprite | undefined) {}

  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const target = (payload.target_scene_id as string) || "";
    const reason = (payload.reason as string) || "";
    const switched = Boolean(payload.switched);
    log.info(`party_decide target=${target} switched=${switched}`);

    const text = switched
      ? `众人一致决定：动身前往新的地点（${target}）。${reason}`
      : `众人决定：留在原地继续探索。${reason}`;
    await this._playNarration(text);
  }

  /** 播放决策旁白（用任意可见角色气泡，无则按内容时长停留）/ Play decision narration */
  private _playNarration(text: string): Promise<void> {
    return new Promise((resolve) => {
      const done = () => resolve();
      const sprite = this.getAnySprite();
      if (sprite) {
        sprite.showExploreRecord(text, done);
      } else {
        setTimeout(done, speedMs(contentDuration(text)));
      }
    });
  }

  clear(): void {
    // 无内部队列，预留接口 / no internal queue, reserved for symmetry
  }
}
