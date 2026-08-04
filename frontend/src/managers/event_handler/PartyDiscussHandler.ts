/** 集体讨论事件处理器 / Party discussion event handler — 多人对话（仅信息交流） */
import { createLogger } from "../../utils/logger";
const log = createLogger("PartyDiscussHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";
import { speedMs } from "../../config/playback";
import { contentDuration } from "../../utils/contentDuration";

export class PartyDiscussHandler {
  private dialogueQueue: Array<{ speaker_id: string; text: string }> = [];
  private isPlaying = false;
  private timer?: number;

  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getAnySprite: () => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private followSprite: (sprite: any) => void
  ) {}

  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const dialogue = (payload.dialogue as Array<{ speaker_id: string; text: string }>) || [];
    log.info(`party_discuss turns=${dialogue.length}`);

    if (dialogue.length) {
      await this._playTurns(dialogue);
    }
  }

  /** 顺序播放多轮发言 / Play discussion turns sequentially */
  private _playTurns(turns: Array<{ speaker_id: string; text: string }>): Promise<void> {
    return new Promise((resolve) => {
      this.dialogueQueue.push(...turns);
      this._playNext(resolve);
    });
  }

  /** 逐条出队播放；无发言人精灵时按文本时长定时跳过 / Play turns one-by-one, skip with timer if sprite missing */
  private _playNext(onDone?: () => void): void {
    if (this.dialogueQueue.length === 0) {
      this.isPlaying = false;
      onDone?.();
      return;
    }
    this.isPlaying = true;
    const turn = this.dialogueQueue.shift()!;
    const sprite = this.getSprite(turn.speaker_id);
    if (sprite) this.followSprite(sprite.rawSprite);

    const advance = () => {
      this.isPlaying = false;
      this._playNext(onDone);
    };
    if (sprite) {
      sprite.say(turn.text, advance);
    } else {
      log.warn("[PartyDiscussHandler] speaker not found:", turn.speaker_id);
      this.timer = window.setTimeout(advance, speedMs(contentDuration(turn.text)));
    }
  }

  /** 清空队列与定时器，用于切换场景或重置 / Clear queue and timer on scene switch or reset */
  clear(): void {
    this.dialogueQueue = [];
    this.isPlaying = false;
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = undefined;
    }
  }
}
