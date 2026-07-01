/** 格子坐标 ↔ 世界坐标 / Grid ↔ World coordinate conversion */
/** kb/09: 双坐标模式 — 存储用整数 tile 坐标，渲染用像素坐标 */

/** tile 坐标 → 像素中心 / Tile coords → pixel center */
export function gridToWorld(tx: number, ty: number, tileSize: number): { wx: number; wy: number } {
  return { wx: tx * tileSize + tileSize / 2, wy: ty * tileSize + tileSize / 2 };
}

/** 像素坐标 → tile 坐标 / Pixel coords → tile coords */
export function worldToGrid(wx: number, wy: number, tileSize: number): { tx: number; ty: number } {
  return { tx: Math.floor(wx / tileSize), ty: Math.floor(wy / tileSize) };
}
