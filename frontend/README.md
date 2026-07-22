# AIGameWorld 前端 / Frontend

基于 Phaser 3 的 2D 瓦片地图渲染与事件回放客户端。TypeScript + Vite。

## 快速开始 / Quick Start

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

需先启动后端（默认 http://localhost:8000），见 [backend/README.md](../backend/README.md)。

## 核心架构 / Architecture

- **TickPlayer** — Tick 播放器状态机（idle/running/paused），HTTP 轮询拉取后端事件 + ACK 确认消费进度（syncDisplayTick）
- **EventManager** — 事件分发器，按类型逐条串行分发到对应 Handler，支持暂停中断
- **Handlers** — 各事件类型驱动 Phaser 动画：地图切换、精灵移动（tween 路径）、气泡对话、战斗特效、DM 叙事浮字
- **Store** — WorldStore（启动时写一次）+ TickStore（每 tick 更新）分离，前端不写坐标，坐标唯一来源是后端 scene_setup 事件
- **DOM 面板** — 控制栏（跑 N Tick/循环/暂停/重置/倍速 1x~4x）、事件面板、DM 叙事面板、角色面板

## 测试 / Tests

```bash
npx playwright test    # 38 个 E2E 测试（自动启动后端 mock 环境 + Vite dev server）
```

## 技术栈 / Stack

TypeScript / Phaser 3 / Vite / Playwright / 瓦片地图（Tiled TMX + 多 tileset）
