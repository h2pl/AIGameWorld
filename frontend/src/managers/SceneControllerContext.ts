/** Scene 依赖上下文 / Scene dependency context
 *
 * 把 GameScene 对 handler 的依赖收敛到一个接口，避免 handler 反向引用场景类。
 * / A narrow context interface so handlers don't need to import GameScene.
 */
import type { CharacterManager } from "./CharacterManager";
import type { MovementManager } from "./MovementManager";

export interface SceneControllerContext {
  /** Phaser 场景实例 / Phaser scene instance */
  readonly scene: Phaser.Scene;
  /** 获取角色管理器 / Get character manager */
  getCharManager(): CharacterManager | undefined;
  /** 获取移动管理器 / Get movement manager */
  getMovementManager(): MovementManager | undefined;
  /** 场景是否已构建完成 / Whether the playable scene has been built */
  isSceneBuilt(): boolean;
}
