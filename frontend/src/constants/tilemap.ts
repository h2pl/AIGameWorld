/** 地图常量 / Tilemap Constants */
export const TILEMAP = {
  TILE_SIZE: 32,
  MARGIN: 1,
  SPACING: 2,
  WALK_SPEED: 200, // ms per tile / 每格移动毫秒数
  LAYERS: {
    BELOW: "Below Player",
    WORLD: "World",
    ABOVE: "Above Player",
    OBJECTS: "Objects",
    SPAWN_POINT: "Spawn Point",
  },
} as const;
