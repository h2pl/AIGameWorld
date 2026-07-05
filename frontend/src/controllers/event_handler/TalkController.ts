/** 对话事件处理器 / Talk event handler */
import type { EventData } from "../../types";
import type { EventController } from "../base/EventController";
import type { SceneControllerContext } from "../SceneControllerContext";

export class TalkController implements EventController {
  private dialogueQueue: Array<{ speaker_id: string; text: string }> = [];
  private isPlayingDialogue = false;
  private dialogueTimer?: number;

  constructor(private ctx: SceneControllerContext) {}

  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;

    const pcId = String(payload.pc_id || "");
    const targetPos = payload.target_position as { x: number; y: number } | undefined;

    // 1. 先走到目标旁边 / Approach target first
    if (pcId && targetPos) {
      const sprite = this.ctx.getCharManager()?.getSprite(pcId);
      const movementManager = this.ctx.getMovementManager();
      if (sprite && movementManager) {
        await movementManager.walkToAdjacent(sprite, targetPos.x, targetPos.y);
      }
    }

    // 2. 显示对话 / Show dialogue
    const result = payload.result as Record<string, unknown> | undefined;
    const turns = result?.turns as Array<{ speaker_id: string; text: string }> | undefined;
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
    if (this.isPlayingDialogue || this.dialogueQueue.length === 0) {
      if (this.dialogueQueue.length === 0) onDone?.();
      return;
    }
    this.isPlayingDialogue = true;
    const turn = this.dialogueQueue.shift()!;
    const sprite = this.ctx.getCharManager()?.getSprite(turn.speaker_id);
    const advance = () => {
      this.isPlayingDialogue = false;
      this._playNextDialogue(onDone);
    };
    if (sprite) {
      sprite.say(turn.text, advance);
    } else if (!this.ctx.isSceneBuilt()) {
      // 场景尚未构建完成，稍等重试 / Scene not ready yet, retry shortly
      this.dialogueTimer = window.setTimeout(() => {
        this.dialogueQueue.unshift(turn);
        this.isPlayingDialogue = false;
        this._playNextDialogue(onDone);
      }, 200);
    } else {
      console.warn("[TalkController] dialogue speaker not found:", turn.speaker_id);
      // 找不到说话者时短暂停留后继续 / Brief pause if speaker missing
      this.dialogueTimer = window.setTimeout(advance, 600);
    }
  }
}
