/** 前端类型定义 / Frontend Type Definitions */

/** 场景数据 / Scene data */
export interface SceneData {
  id: string;
  name: string;
  type: "outdoor" | "indoor" | "underground" | "village";
  description: string;
  spawn_x?: number;
  spawn_y?: number;
  exits: ExitData[];
  landmarks: LandmarkData[];
  environment: { weather?: string; time_of_day?: string };
}

export interface ExitData {
  target_scene: string;
  position: { x: number; y: number };
  description: string;
}

export interface LandmarkData {
  id: string;
  name: string;
  position: { x: number; y: number };
}

/** 角色数据 / Character data */
export interface CharacterData {
  id: string;
  name: string;
  role: string;
  race: string | null;
  status: "active" | "dead" | "left";
  scene_id: string;
  position_x: number;
  position_y: number;
  attributes: AttributesData;
  combat: CombatData | null;
  personality: string;
  /** PC 特有 / PC only */
  character_arc?: CharacterArcData;
  /** Actor 特有 / Actor only */
  functions?: string[];
  /** true=PC, false=Actor */
  is_pc: boolean;
}

export interface AttributesData {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

export interface CombatData {
  hp: number;
  max_hp: number;
  ac: number;
  attack_bonus: number;
  damage_dice: string;
  initiative: number;
}

export interface CharacterArcData {
  stage: string;
  description: string;
}

/** 物品 / Item */
export interface ItemData {
  id: string;
  name: string;
  item_type: string;
  rarity: string;
  description: string;
}

/** Tick 快照 / Tick snapshot (WebSocket 推送) */
export interface TickUpdate {
  type: "phase_update" | "dm_narrative" | "tick_complete";
  phase?: number;
  data: TickUpdateData;
}

export interface TickUpdateData {
  tick: number;
  actions?: ActionData[];
  events?: EventData[];
  narrative?: string;
  state_snapshot?: WorldSnapshot;
  errors?: string[];
}

export interface ActionData {
  character_id: string;
  action_type: string;
  reasoning?: string;
}

export interface EventData {
  type: string;
  tick?: number;
  description?: string;
  payload?: Record<string, unknown>;
  source?: string;
  target?: string;
  /** 全局递增序号，用于面板去重 / Global monotonic seq for dedup */
  seq?: number;
}

export interface WorldSnapshot {
  characters: CharacterData[];
  scene_objects: SceneObjectData[];
  current_scene: string;
  /** scene_name→position坐标 */
  character_positions: Record<string, { x: number; y: number }>;
}

export interface SceneObjectData {
  id: string;
  name: string;
  object_type: string;
  scene_id: string;
  position_x: number;
  position_y: number;
}

/** 初始世界状态 / Initial world state (HTTP API 返回) */
export interface InitialWorldState {
  world_id: string;
  data_tick: number;
  display_tick: number;
  llm_mock?: boolean;
  data_mode?: string;
  db_name?: string;
  mock_dataset?: string;
  scenes: SceneData[];
  characters: CharacterData[];
  items: ItemData[];
  scene_objects: SceneObjectData[];
}
