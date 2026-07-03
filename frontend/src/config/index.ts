/** 前端配置 / Frontend Configuration — HTTP API（已移除 WebSocket）*/
const DEFAULT_API_ORIGIN = `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_ORIGIN).replace(/\/$/, "");

/** 画布 / Canvas */
/** 瓦片 / Tile */
/** 颜色 / Colors */
/** API / API */
export const CONFIG = {
  CANVAS: { width: 960, height: 640 },
  TILE: { size: 32, cols: 30, rows: 20 },
  COLOR: {
    background: 0x1a1a2e as number,
    tile_empty: 0x16213e as number,
    tile_floor: 0x2d4059 as number,
    tile_wall: 0x4a5568 as number,
    tile_door: 0x8b6914 as number,
    tile_outdoor: 0x2e4a2e as number,
    pc_border: 0xffd700 as number,
    pc_color: 0x3498db as number,
    actor_colors: [0xe74c3c, 0x2ecc71, 0xf39c12, 0x9b59b6, 0x1abc9c] as number[],
    text: "#ffffff" as string,
    text_dim: "#8899aa" as string,
  },
  API: { base: API_BASE, health: "/health", worldState: "/api/world" },
};
