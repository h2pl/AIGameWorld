/** 探索事件处理器 / Explore event handler */
import { gameStore } from "../../state/GameStore";
import type { EventData } from "../../types";
import type { EventController } from "../base/EventController";
import type { SceneControllerContext } from "../SceneControllerContext";

export class ExploreController implements EventController {
  constructor(private ctx: SceneControllerContext) {}

  async handle(ev: EventData): Promise<void> {
    // 解析事件负载 / Parse event payload
    const payload = ev.payload;
    if (!payload) return;

    // 提取角色 ID 与路径点 / Extract pc id and waypoints
    const pcId = String(payload.pc_id || "");
    const waypoints = payload.waypoints as Array<{ x: number; y: number }> | undefined;
    const finalX = Number(payload.final_x ?? 0);
    const finalY = Number(payload.final_y ?? 0);
    if (!pcId || !waypoints?.length) return;

    // 获取角色精灵与移动管理器 / Get character sprite and movement manager
    const sprite = this.ctx.getCharManager()?.getSprite(pcId);
    if (!sprite) return;
    const movementManager = this.ctx.getMovementManager();
    if (!movementManager) return;

    // 把最终坐标也加入路径末尾 / Append final destination to route
    const allWaypoints = [...waypoints, { x: finalX, y: finalY }];
    return new Promise((resolve) => {
      movementManager.walkRoute(sprite, allWaypoints, {
        onComplete: (finalTx, finalTy) => {
          // 走完后同步坐标到 store，避免下次 sync 瞬移 / Sync final pos to store after walk
          const st = gameStore.getState();
          st.character_positions[pcId] = { x: finalTx, y: finalTy };
          const ch = st.characters.find((c) => c.id === pcId);
          if (ch) {
            ch.position_x = finalTx;
            ch.position_y = finalTy;
          }
          console.log("[ExploreController] explore done: %s → (%d,%d)", pcId, finalTx, finalTy);
          resolve();
        },
      });
      console.log(
        "[ExploreController] explore: %s through %d waypoints → (%d,%d)",
        pcId,
        waypoints.length,
        finalX,
        finalY
      );
    });
  }
}
