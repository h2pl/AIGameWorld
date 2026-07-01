/** 缓存键 / Cache Keys */
export const KEY = {
  IMAGE: {
    TUXEMON: "tuxemon",
    DESERT: "desert-tiles",
  },
  TILEMAP: {
    TUXEMON: "tuxemon-map",
    FOREST: "forest-map",
    DESERT: "desert-map",
  },
  SPRITE: {
    SPACEMAN: "spaceman",
  },
} as const;

/** 场景 → 地图映射 / Scene → Tilemap mapping */
export const SCENE_MAP: Record<string, string> = {
  "village_elderwood": "tuxemon-map",
  "forest_north": "forest-map",
  "desert": "desert-map",
};
