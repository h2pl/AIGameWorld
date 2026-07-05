/** 场景设置事件处理器 / Scene setup event handler — 从 scene_info 设置当前场景和 PC 坐标 */
import { tickStore } from "../../state/TickStore";
import type { EventData } from "../../types";

export class SceneSetupHandler {
  /** 消费 scene_setup 事件 / Consume scene_setup event */
  handle(ev: EventData): void {
    const payload = ev.payload;
    if (!payload) return;

    const sceneId = String(payload.scene_id || "");
    if (!sceneId) return;

    const scene = payload.scene as Record<string, unknown> | undefined;
    const mapKey = scene ? String(scene.map_key || "") : "";
    const positions = payload.pc_positions as Record<string, { x: number; y: number }> | undefined;

    tickStore.setSceneReady(sceneId, mapKey, positions);
  }
}
