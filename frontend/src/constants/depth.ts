/** 深度层级 / Depth Layers */
export const DEPTH = {
  BELOW_PLAYER: 0,    // Below Player 层
  WORLD: 1,            // World 层
  CHARACTER: 10,       // 角色
  ABOVE_PLAYER: 20,    // Above Player（树冠）
  HUD: 50,             // HUD 面板
} as const;
