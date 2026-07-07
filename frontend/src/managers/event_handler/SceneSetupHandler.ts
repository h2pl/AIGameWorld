/** 场景设置事件处理器 / Scene setup event handler — 直连 GameScene + 更新 WorldStore */
import type { EventData } from "../../types";
import { worldStore } from "../../state/WorldStore";

export type SceneSetupData = {
  sceneId: string;
  sceneName: string;
  mapKey: string;
  extJson: Record<string, string>;
  pcs: any[];
  actors: any[];
  sceneObjects: any[];
};

export class SceneSetupHandler {
  constructor(private ensureScene: (data: SceneSetupData) => Promise<void>) {}

  /** 处理场景设置事件，构建场景后更新 store / Handle scene_setup, build then update store */
  async handle(ev: EventData): Promise<void> {
    const payload = ev.payload;
    if (!payload) return;
    const sceneId = String(payload.scene_id || "");
    if (!sceneId) return;

    // 解析场景数据 / Parse scene data
    const scene = payload.scene as Record<string, unknown> | undefined;
    const sceneName = scene ? String(scene.name || "") : "";
    const mapKey = scene ? String(scene.map_key || sceneId) : sceneId;
    const extJson: Record<string, string> = scene?.ext_json
      ? JSON.parse(scene.ext_json as string)
      : {};

    await this.ensureScene({
      sceneId,
      sceneName,
      mapKey,
      extJson,
      pcs: (payload.pcs || []) as any[],
      actors: (payload.actors || []) as any[],
      sceneObjects: (payload.scene_objects || []) as any[],
    });

    // 场景构建完成后更新 store / Update store after scene built
    worldStore.setCurrentScene(sceneId, sceneName);
  }
}
