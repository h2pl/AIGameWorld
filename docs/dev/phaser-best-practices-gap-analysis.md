# Phaser 最佳实践差距分析

> 对照 `multi-agent-manager/skills/frontend/phaser-gamedev/knowledgebase/` 中 18 篇最佳实践文档，
> 逐项分析 AIGameWorld 前端当前实现与规范的差距，按优先级和影响排列。

---

## 一、场景架构（01-scene-architecture）

### 1.1 缺少 Preloader 场景 — 高优先级

**规范**: Boot → Preloader → MainMenu → Game → GameOver，Preloader 负责全量资源加载+进度条。

**现状**: 只有 `Boot` → `GameScene`。Boot 在 `preload()` 中加载所有 tileset/tilemap，无进度反馈。

**差距**:
- 所有资源一次性在 Boot 中加载，加载失败时无用户可见反馈
- 没有 loading 进度条，大世界场景多时体验差
- Boot 既要加载又要处理错误，职责不清

**建议**:
- 拆分 Boot（只做 registry 初始化）+ Preloader（全量资源 + 进度条 + 错误重试）
- Preloader 展示资源加载百分比，完成后再 `scene.start('Game')`

### 1.2 缺少 Parallel Scene UI Overlay — 中优先级

**规范**: 用 `scene.launch('GameUI')` 将 HUD 作为独立并行场景运行，与 Game 解耦。

**现状**: HUD（血条、名字标签）是 DOM 元素（CSS overlay），不是 Phaser 场景。GameHUD 在 GameScene 内部创建。

**差距**:
- DOM HUD 与 Canvas 不同渲染管线，性能开销大
- 无法利用 Phaser 的 depth sorting、camera follow 等 HUD 管理特性

**建议**: 当前 DOM 方案对于观察者模式可接受，但如果后续要支持玩家交互（点击 PC 使用技能），建议将核心 HUD 元素迁入 Phaser 的 Parallel UI Scene。

### 1.3 缺少场景过渡视觉反馈 — 低优先级

**规范**: 场景切换配合 fade/flash/shader 过渡。

**现状**: `_buildScene` 末尾有 `cameras.main.fadeIn(400)`，但场景销毁时没有 fadeOut。

**建议**: 在 `_destroyScene` 前增加 `cameras.main.fadeOut(200)` 过渡。

---

## 二、代码组织（17-code-organization）

### 2.1 初始化顺序不严格 — 中优先级

**规范**: `create()` 按 initVariables → initCamera → initPhysics → createBackground → createGroups → createLevel → createPlayer → createEnemies → initAnimations → initInput → setupCollisions → createUI → startGame 顺序。

**现状**: GameScene.create() 中初始化顺序是：ts → mapManager → hud → eventManager → handlers → 注册 → reset 事件 → recoverFromReload → testSeam。实际场景构建在 `_buildScene` 中。

**差距**: `_buildScene` 内部顺序合理（地图 → 地形 → 角色 → HUD → 输入 → 相机），但 create() 本身没有严格按规范拆分为多个 init 方法。

**建议**: 将 create() 拆分为 `_initVariables()`, `_initManagers()`, `_registerEvents()`, `_setupInput()` 等方法，提高可读性。

### 2.2 Constants 管理分散 — 低优先级

**规范**: 独立 SpriteKeys、AnimationKeys、AudioKeys 文件，集中管理所有字符串常量。

**现状**: 常量分布在 `config/index.ts`、`constants/tilemap.ts`、`constants/key.ts` 中，字符串 key（如 `"fighter_fb"`, `"actor_fb"`）散落在各处。

**差距**: 纹理 key、动画 key 等字符串硬编码在 `makeCharTexture`、`CharacterSprite` 构造函数中，没有集中管理。

**建议**: 创建 `constants/assets.ts`，集中定义所有纹理 key、动画 key、音频 key。

---

## 三、状态管理（07-state-management）

### 3.1 未使用 init() 重置状态 — 高优先级

**规范**: 可重置的状态放在 `init()` 中而非 `constructor()`，因为 scene restart 不会重新调用 constructor。

**现状**: GameScene 的 `constructor()` 只调了 `super({ key: "Game" })`，状态都在类字段声明时初始化（`sceneBuilt = false`, `_cameraZoom = 1.0` 等）。重置走 `_handleReset()` 事件。

**差距**: 如果场景被 Phaser 的 `scene.restart()` 重启（虽然当前没有），类字段不会重置。当前通过 `_handleReset` 手动重置，不够优雅。

**建议**: 添加 `init()` 方法，在其中重置所有状态字段，确保 scene restart 场景安全。

### 3.2 未使用 Phaser Registry 做跨场景通信 — 中优先级

**规范**: 使用 `this.registry.set/get` 管理跨场景数据，监听 `changedata-*` 事件。

**现状**: 跨场景通信混合了多种方式：
- `game.registry` 存了 `eventManager`, `tickPlayer`, `displayTick`, `initialWorldState`
- DOM `CustomEvent` 做了大量 UI ↔ Game 通信（`tick-start`, `tick-event`, `play-paused`, `character-selected` 等）
- `window.addEventListener` 直接在 GameScene 中监听 DOM 事件

**差距**: DOM 事件无法被 Phaser 场景生命周期管理，shutdown 时必须手动清理。混用两种事件系统增加复杂度。

**建议**: Phaser 内部通信统一用 `this.events`/`this.registry`，DOM 事件仅用于 DOM 面板 ↔ Phaser 的桥接层。

### 3.3 未使用 GameObject.setData() — 低优先级

**规范**: 用 `sprite.setData()` 存储自定义属性，不污染 sprite 命名空间。

**现状**: CharacterSprite 自己维护 `thinkCount`、`walkQueue`、`walkSpeed` 等属性。

**差距**: 当前 CharacterSprite 是自定义类而非直接扩展 Sprite，所以直接属性访问更自然。但如果未来要批量操作精灵数据，setData 更灵活。

**建议**: 当前做法可接受，暂不改动。

---

## 四、移动模式（04-movement-patterns）

### 4.1 移动应基于 Phaser Timer 而非递归 Tween — 高优先级

**规范**: 对于网格/回合制游戏，推荐 Timer-Based Movement 或 Time-Based Discrete Movement，而非每步递归创建 Tween。

**现状**: `CharacterSprite.walkNext()` 每走一步就 `this.scene.tweens.add()`，递归回调下一步。多 PC × 多步骤 = 大量 Tween 对象。

**差距**:
- 每步创建/销毁 Tween 对象，GC 压力大
- 倍速切换时需要 killTweensOf + 重建，不够流畅
- 无法统一暂停/恢复所有移动

**建议**:
- 方案 A：改用 `scene.time.addEvent` + 手动插值，减少 Tween 分配
- 方案 B：使用单个 Tween 的 `onUpdate` 回调自行插值，一次 Tween 完成整条路径
- 方案 C：用 Phaser 的 `tweens.chain()` 替代递归

### 4.2 缺少路径碰撞/障碍检测 — 中优先级

**规范**: 网格移动应有边界检查和碰撞验证。

**现状**: `calcSteps()` 直接算直线/曼哈顿路径，不检查 tilemap 碰撞层。角色可能穿过墙壁/水面。

**建议**: 在 `calcSteps` 或 `MovementManager.walkTo` 中加入 tilemap 碰撞层检查，不可通行时绕路或原地等待。

---

## 五、对象池与内存（08-object-pooling-memory）

### 5.1 DialogueBubble 频繁创建销毁 — 高优先级

**规范**: 频繁创建/销毁的对象应使用对象池，预创建后 enable/disable 复用。

**现状**: 每次 `CharacterSprite.say()`/`showExploreRecord()`/`think()` 都 `new DialogueBubble()`，用完 `destroy()`。一个 tick 内可能有 5+ 个角色各显示一次气泡。

**差距**:
- DialogueBubble 包含 Container + Graphics + Text，每次创建至少 3 个 GameObject
- `_splitPages` 方法中还有临时 Text 对象创建/销毁用于计算分页
- GC 压力在多 PC 场景下可能造成帧率抖动

**建议**:
- 创建 DialogueBubblePool，预分配 5-8 个气泡
- `show()` 时从池中获取，`hide()` 时回池
- 分页计算用缓存或预计算替代临时 Text 对象

### 5.2 TerrainSprite 未使用 Group — 中优先级

**规范**: 同类对象使用 Phaser.Group 管理，支持批量操作。

**现状**: `terrainSprites` 是普通数组 `Phaser.GameObjects.Sprite[]`，手动遍历销毁。

**建议**: 改用 `this.add.group()` 或 `this.physics.add.staticGroup()`（地形是静态的），获得 `countActive()`、`getChildren()` 等批量操作能力。

### 5.3 Dynamic Texture 未清理 — 中优先级

**规范**: 动态创建的纹理必须显式销毁，否则内存泄漏。

**现状**: `makeCharTexture` 和 `makeObjectTexture` 用 `textures.addDynamicTexture` 或 `textures.createCanvas` 创建纹理，但 `_destroyScene` 中没有清理这些纹理。

**建议**: 在 `_destroyScene` 中遍历并销毁场景相关的动态纹理，或在 MapManager 中跟踪已创建的纹理 key。

---

## 六、自定义游戏对象（10-custom-game-objects）

### 6.1 CharacterSprite 未继承 Phaser Sprite — 高优先级

**规范**: 需要物理和渲染的实体应 `extends Phaser.Physics.Arcade.Sprite`，自注册到 scene，利用 `preUpdate` 生命周期。

**现状**: `CharacterSprite` 是纯组合模式（包含 `Phaser.GameObjects.Sprite` 引用），不是 Sprite 子类。

**差距**:
- 无法使用 `preUpdate` 生命周期，全靠外部（handler）驱动
- 无法加入 Phaser Group（Group 要求 classType 是 Phaser.GameObjects 子类）
- 无法使用 Arcade Physics（碰撞、重叠检测）
- 需要手动暴露 `rawSprite` 属性给 camera follow 等

**建议**: 重构为 `class CharacterSprite extends Phaser.Physics.Arcade.Sprite`：
- `constructor` 中 `scene.add.existing(this); scene.physics.add.existing(this);`
- 移动逻辑放入 `preUpdate`
- 名字标签、血条、泡泡作为子对象

### 6.2 缺少 preUpdate 生命周期 — 中优先级

**规范**: 自定义 Sprite 应在 `preUpdate` 中处理每帧逻辑。

**现状**: CharacterSprite 没有 `preUpdate`/`update`，所有逻辑（跟随更新、气泡位置）由外部调用 `updateFollowers()` 触发。

**差距**: 如果忘记调用 `updateFollowers()`，名字标签/血条/气泡会停在旧位置。这已经在 Tween 的 `onUpdate` 中调用了，但不够健壮。

**建议**: 继承 Phaser.Sprite 后在 `preUpdate` 中自动调用 `updateFollowers()`。

---

## 七、UI/HUD 模式（11-ui-hud-patterns）

### 7.1 Depth 管理不一致 — 中优先级

**规范**: 用 `setDepth()` 统一层级管理：背景=0, 游戏=5-10, HUD=50-100。

**现状**: Depth 分散定义：
- `DEPTH.CHARACTER` 在 constants 中
- DialogueBubble 硬编码 `setDepth(200)`
- 名字标签/血条硬编码 `setDepth(30)`
- 地形物体用 `DEPTH.CHARACTER - 1`

**差距**: 魔法数字和常量混用，层级可能冲突。

**建议**: 在 `constants/depth.ts` 中统一定义所有层级常量。

### 7.2 血条每帧重建 — 低优先级

**规范**: 静态/低频变化的 UI 应避免每帧重绘。

**现状**: `updateFollowers()` 中 `hpBar.clear()` + `drawHpBar()` 每帧调用（在 Tween onUpdate 中）。血量不变时也在重绘。

**建议**: 只在 `updateHp()` 和位置变化时重绘血条。

---

## 八、Tween 与视觉效果（12-tween-visual-effects）

### 8.1 渐入渐出缺少缓动函数 — 低优先级

**规范**: 使用 `ease: 'Power2'`, `'Cubic.easeInOut'` 等缓动函数让动画更自然。

**现状**: DialogueBubble 的渐入渐出都用默认缓动（Linear），移动用 `ease: 'Linear'`（这是正确的）。

**建议**: 气泡渐入改用 `ease: 'Cubic.easeOut'`，渐出改用 `ease: 'Cubic.easeIn'`，视觉效果更佳。

### 8.2 未使用 Tween Chain — 低优先级

**规范**: 连续动画序列用 `tweens.chain()` 管理。

**现状**: 移动路径用递归 `walkNext()` 实现，气泡用 `_advance()` 递归。

**建议**: 对于固定序列动画（如受伤闪烁），可使用 `tweens.chain()`。

### 8.3 缺少 Camera 效果 — 低优先级

**规范**: 战斗/重要事件配合 camera shake/flash 效果。

**现状**: 场景构建后有 `fadeIn(400)`，但没有战斗震屏、受伤闪烁等效果。

**建议**: 在 CombatHandler 中添加 `cameras.main.shake(200, 0.01)` 震屏效果。

---

## 九、资源管理（02-asset-management）

### 9.1 缺少进度反馈 — 中优先级

**规范**: 两阶段加载：Boot 只加载进度条资源，Preloader 加载全部并展示进度。

**现状**: Boot 场景加载所有资源，无进度展示。

**建议**: 拆分 Boot + Preloader，Preloader 中 `this.load.on('progress', ...)` 更新进度条。

### 9.2 缺少 Texture Atlas — 低优先级

**规范**: 多精灵合并为 Atlas，减少 HTTP 请求和 Draw Call。

**现状**: 每个 tileset 是独立图片，角色纹理通过 Canvas 动态生成。

**差距**: 对于当前 tileset 数量（5-10 个），独立加载可接受。如果后续增加大量精灵图，应改为 Atlas。

---

## 十、性能优化（16-performance-optimization）

### 10.1 Event-Driven vs Polling — 中优先级

**规范**: 事件驱动优于轮询，用 Physics Overlap 替代距离检查。

**现状**: `_setupInput` 中用 `pointerdown` + `getWorldPoint` + `Math.abs` 距离检查来做角色点击选择。

**差距**: 遍历所有 PC 和 Actor 做距离比较，不如用 Phaser 的 `setInteractive()` + `on('pointerdown')` 直接响应。

**建议**: 已经在 CharacterSprite 上设置了 `setInteractive()`，但 GameScene 的 `_setupInput` 还在手动计算距离。应改为直接监听 sprite 的 pointerdown 事件。

### 10.2 TerrainSprite 应使用 StaticGroup — 中优先级

**规范**: 不可移动的物体使用 StaticGroup，性能更好。

**现状**: 地形物体用普通 Sprite 数组，没有利用 StaticGroup 的优化。

**建议**: 改用 `this.physics.add.staticGroup()`，一次 `refreshBody()` 批量优化碰撞体。

---

## 十一、常见陷阱（common-pitfalls）

### 11.1 shutdown 未清理所有监听器 — 高优先级

**规范**: `shutdown()` 中必须清理所有事件监听器和定时器。

**现状**: GameScene.shutdown() 清理了 `scene-reset` 事件和 `play-paused/play-resumed` DOM 监听，但：
- 没有清理 `character-clicked` 事件
- 没有 kill 所有活跃 Tween
- 没有清理 window 上的 `tick-start`、`tick-event` 等自定义事件监听

**建议**: 在 shutdown 中全面清理：
```typescript
shutdown(): void {
  this.tweens.killAll();
  this.pcManager?.destroy();
  this.actorManager?.destroy();
  this.game.events.off("scene-reset");
  window.removeEventListener("play-paused", this._onPlayPaused);
  window.removeEventListener("play-resumed", this._onPlayResumed);
  // 清理所有 DOM 事件监听
}
```

### 11.2 DialogueBubble._splitPages 临时对象泄漏 — 中优先级

**规范**: 不要在热路径中频繁创建/销毁对象。

**现状**: `_splitPages` 对每个气泡执行二分查找，每次迭代 `scene.add.text(...)` 创建临时 Text + `.destroy()`，一个气泡最多创建 ~20 个临时 Text 对象。

**建议**: 用一个持久的"测量 Text"（隐藏不销毁）来替代，或缓存常用尺寸。

---

## 十二、游戏循环模式（14-game-loop-patterns）

### 12.1 GameScene 没有 update() — 符合规范

**规范**: 回合制/事件驱动游戏可不写 update()，用 Timer + Tween + 事件驱动。

**现状**: GameScene 没有 `update()` 方法，全靠事件驱动 + Tween。**这完全符合规范**，是正确的做法。

### 12.2 EventManager 使用 Promise.race 实现暂停 — 可优化

**规范**: 使用 Phaser Timer 的 `paused` 属性控制暂停。

**现状**: EventManager 用 `_untilPaused()` 轮询 `playState.playing`（80ms 间隔）来检测暂停信号。

**差距**: 轮询有延迟（最大 80ms），不够即时。

**建议**: 改用 Promise + resolve 回调模式：
```typescript
private _pauseResolver: (() => void) | null = null;
pause() { this._pauseResolver?.(); }
// 在 processTick 中 await Promise.race([handler, new Promise(r => { this._pauseResolver = r; })])
```

---

## 优先级总结

| 优先级 | 问题 | 文件 |
|--------|------|------|
| **P0 高** | CharacterSprite 未继承 Phaser.Sprite | CharacterSprite.ts |
| **P0 高** | DialogueBubble 频繁创建销毁（需对象池） | DialogueBubble.ts |
| **P0 高** | 移动递归 Tween 应改为 Timer/Chain | CharacterSprite.ts |
| **P0 高** | shutdown 未清理所有监听器 | GameScene.ts |
| **P0 高** | 缺少 Preloader 场景 | scenes/ |
| **P1 中** | init() 未重置状态 | GameScene.ts |
| **P1 中** | 跨场景通信混用 DOM + Registry | 全局 |
| **P1 中** | 地形未用 StaticGroup | GameScene.ts |
| **P1 中** | 动态纹理未清理 | GameScene.ts |
| **P1 中** | 缺少碰撞/障碍检测 | MovementManager.ts |
| **P1 中** | 角色选择用手动距离检查而非 Interactive | GameScene.ts |
| **P1 中** | Depth 常量管理不一致 | 全局 |
| **P1 中** | _splitPages 临时 Text 对象 | DialogueBubble.ts |
| **P2 低** | 场景销毁无 fadeOut 过渡 | GameScene.ts |
| **P2 低** | Constants 管理分散 | constants/ |
| **P2 低** | 血条每帧重建 | CharacterSprite.ts |
| **P2 低** | 缓动函数缺失 | DialogueBubble.ts |
| **P2 低** | 缺少 Camera shake 效果 | CombatHandler.ts |
| **P2 低** | 缺少 Texture Atlas | assets/ |
