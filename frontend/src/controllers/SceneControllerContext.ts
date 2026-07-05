/** SceneController 依赖上下文 / Scene controller dependency context
 *
 * 把 GameScene 对 controller 的依赖收敛到一个接口，避免 controller 反向引用场景类。
 * / A narrow context interface so controllers don't need to import GameScene.
 */
import type { CharacterManager } from "../managers/CharacterManager";
import type { WalkController } from "./WalkController";

export interface SceneControllerContext {
  /** Phaser 场景实例 / Phaser scene instance */
  readonly scene: Phaser.Scene;
  /** 获取角色管理器 / Get character manager */
  getCharManager(): CharacterManager | undefined;
  /** 获取移动控制器 / Get walk controller */
  getWalkController(): WalkController | undefined;
  /** 场景是否已构建完成 / Whether the playable scene has been built */
  isSceneBuilt(): boolean;
}
