/** 世界状态 / World State — 每个字段都有明确的唯一写者 */
import type { RuntimeConfig } from "../types";

export interface WorldState {
  world_id: string; // main.ts 启动
  runtime: RuntimeConfig; // main.ts 启动
  display_tick: number; // main.ts onTickCallback
  current_scene_id: string; // SceneSetupHandler（scene_setup 事件）
  current_scene_name: string; // SceneSetupHandler（scene_setup 事件）
}

class WorldStore {
  private state: WorldState = {
    world_id: "",
    runtime: { llm_mock: false, data_mode: "real", db_name: "" },
    display_tick: 0,
    current_scene_id: "",
    current_scene_name: "",
  };

  getState(): Readonly<WorldState> {
    return this.state;
  }

  setWorldState(world_id: string, llm_mock: boolean, data_mode: string, db_name: string): void {
    Object.assign(this.state, { world_id, runtime: { llm_mock, data_mode, db_name } });
  }

  setDisplayTick(tick: number): void {
    this.state.display_tick = tick;
  }

  setCurrentScene(id: string, name: string): void {
    this.state.current_scene_id = id;
    this.state.current_scene_name = name;
  }

  clear(): void {
    Object.assign(this.state, { display_tick: 0, current_scene_id: "", current_scene_name: "" });
  }
}

export const worldStore = new WorldStore();
