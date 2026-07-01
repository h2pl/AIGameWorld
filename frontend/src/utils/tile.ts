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

/** 直线路径：从 A 到 B 的中间 tile 世界坐标列表 / Straight-line intermediate tile world-coord steps (Chebyshev) */
export function calcSteps(
  from: { tx: number; ty: number },
  to: { tx: number; ty: number },
  tileSize: number,
): { wx: number; wy: number }[] {
  const dx = to.tx - from.tx;
  const dy = to.ty - from.ty;
  const dist = Math.max(Math.abs(dx), Math.abs(dy));
  if (dist <= 1) {
    // 相邻或同格，直接到目标 / Adjacent or same tile, go directly
    return [gridToWorld(to.tx, to.ty, tileSize)];
  }
  const steps: { wx: number; wy: number }[] = [];
  for (let i = 1; i <= dist; i++) {
    const tx = from.tx + Math.round(dx * i / dist);
    const ty = from.ty + Math.round(dy * i / dist);
    steps.push(gridToWorld(tx, ty, tileSize));
  }
  return steps;
}
