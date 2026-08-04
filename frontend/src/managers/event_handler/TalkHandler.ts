// -- file start -- / file start
/** 对话事件处理器 / Talk event handler */
import { createLogger } from "../../utils/logger";
const log = createLogger("TalkHandler");
import type { CharacterSprite } from "../../gameobjects/CharacterSprite";
import type { MovementManager } from "../MovementManager";
import type { EventData } from "../../types";
import { speedMs } from "../../config/playback";
import { playState } from "../../utils/playState";
import { contentDuration } from "../../utils/contentDuration";

export class TalkHandler {
  private dialogueQueue: Array<{ speaker_id: string; text: string }> = [];
  private isPlayingDialogue = false;
  private dialogueTimer?: number;

  constructor(
    private getSprite: (id: string) => CharacterSprite | undefined,
    private getMovementManager: () => MovementManager | undefined,
    private isSceneBuilt: () => boolean,
    private followSprite: (sprite: any) => void
  ) {}

  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;

    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as Array<{ x: number; y: number }> | undefined;
    log.info(`talk pc=${pcId} target=${payload.target_id} waypoints=${JSON.stringify(waypoints)}`);

    // 镜头跟随当前对话角色 / Camera follows talking PC
    if (pcId) {
      const sprite = this.getSprite(pcId);
      if (sprite) this.followSprite(sprite.rawSprite);
    }

    // 1. 走到目标旁边 / Walk along waypoints to adjacent position
    if (pcId && waypoints?.length) {
      const sprite = this.getSprite(pcId);
      if (sprite && this.getMovementManager()) {
        const mm = this.getMovementManager()!;
        const endPos = waypoints[waypoints.length - 1];
        await mm.walkTo(sprite, endPos.x, endPos.y);
      }
    }

    // 2. 显示对话 / Show dialogue（turns 在 payload 顶层，与后端 event_service 对齐）
    const turns = payload.turns as Array<{ speaker_id: string; text: string }> | undefined;
    if (turns?.length) {
      await this._playDialogueTurns(turns);
    }
  }

  /** 清理对话状态 / Clean up dialogue state */
  clear(): void {
    this.dialogueQueue = [];
    this.isPlayingDialogue = false;
    if (this.dialogueTimer) {
      window.clearTimeout(this.dialogueTimer);
      this.dialogueTimer = undefined;
    }
  }

  /** 顺序播放多轮对话 / Play dialogue turns sequentially */
  private _playDialogueTurns(turns: Array<{ speaker_id: string; text: string }>): Promise<void> {
    return new Promise((resolve) => {
      this.dialogueQueue.push(...turns);
      this._playNextDialogue(resolve);
    });
  }

  /** 播放队列中下一句对话 / Play next dialogue in queue */
  private _playNextDialogue(onDone?: () => void): void {
    // 暂停时立即终止 / Abort immediately when paused
    if (!playState.playing) {
      this.dialogueQueue = [];
      this.isPlayingDialogue = false;
      onDone?.();
      return;
    }
    if (this.isPlayingDialogue || this.dialogueQueue.length === 0) {
      if (this.dialogueQueue.length === 0) onDone?.();
      return;
    }
    this.isPlayingDialogue = true;
    const turn = this.dialogueQueue.shift()!;
    const sprite = this.getSprite(turn.speaker_id);
    const advance = () => {
      this.isPlayingDialogue = false;
      this._playNextDialogue(onDone);
    };
    if (sprite) {
      sprite.say(turn.text, advance);
    } else if (!this.isSceneBuilt()) {
      // 场景尚未构建完成，稍等重试 / Scene not ready yet, retry shortly
      this.dialogueTimer = window.setTimeout(() => {
        this.dialogueQueue.unshift(turn);
        this.isPlayingDialogue = false;
        this._playNextDialogue(onDone);
      }, speedMs(200));
    } else {
      log.warn("[TalkHandler] dialogue speaker not found:", turn.speaker_id);
      this.dialogueTimer = window.setTimeout(advance, speedMs(contentDuration("")));
    }
  }
}
