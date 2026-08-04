/** 地图常量 / Tilemap Constants */
export const TILEMAP = {
  TILE_SIZE: 16, // 默认 16，可由 ext_json.tile_size 覆盖 / Default 16, overridable via ext_json
  MARGIN: 1,
  SPACING: 2,
  WALK_SPEED: 200, // ms per tile / 每格移动毫秒数
} as const;
