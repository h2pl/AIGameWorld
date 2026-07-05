/** 缓存键 / Cache Keys */
export const KEY = {
  IMAGE: {
    TUXEMON: "tuxemon",
    DESERT: "desert-tiles",
  },
  TILEMAP: {
    TUXEMON: "tuxemon-map",
    DESERT: "desert-map",
  },
  SPRITE: {
    SPACEMAN: "spaceman",
  },
} as const;

/** 场景 → 地图 + 出生点 映射 / Scene → Tilemap + Spawn area mapping */
export const SCENE_MAP: Record<string, { map: string; spawn: { x: number; y: number } }> = {
  village_elderwood: { map: "tuxemon-map", spawn: { x: 20, y: 20 } },
  desert: { map: "desert-map", spawn: { x: 10, y: 10 } },
};
