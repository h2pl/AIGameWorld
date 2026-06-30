/** 前端配置 / Frontend Configuration */

export const CONFIG = {
  /** 画布 / Canvas */
  CANVAS: {
    width: 960,
    height: 640,
  },

  /** 瓦片地图 / Tile map */
  TILE: {
    size: 32,          // 格子像素 / Tile pixel size
    cols: 30,           // 列数 / Columns (=960/32)
    rows: 20,           // 行数 / Rows (=640/32)
  },

  /** 颜色主题 / Color theme */
  COLOR: {
    background: 0x1a1a2e as number,
    tile_empty: 0x16213e as number,
    tile_floor: 0x2d4059 as number,
    tile_wall: 0x4a5568 as number,
    tile_door: 0x8b6914 as number,
    tile_outdoor: 0x2e4a2e as number,
    pc_border: 0xffd700 as number,
    pc_color: 0x3498db as number,
    actor_colors: [
      0xe74c3c, 0x2ecc71, 0xf39c12, 0x9b59b6, 0x1abc9c,
    ] as number[],
    text: "#ffffff" as string,
    text_dim: "#8899aa" as string,
  },

  /** 后端 API / Backend API */
  API: {
    base: "http://localhost:8000",
    ws: "ws://localhost:8000/ws",
    health: "/health",
    worldState: "/api/pack",
  },
};
