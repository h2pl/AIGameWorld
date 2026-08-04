/** 场景列表 / Scene list — main.ts 启动时设置，Boot 预加载时读取 */
export let sceneList: any[] = [];
export function setSceneList(scenes: any[]): void {
  sceneList = scenes;
}
