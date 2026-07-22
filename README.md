# AIGameWorld

> LLM 驱动的 Multi-Agent 游戏世界模拟引擎。DM Agent 创造情境，PC Agent 主角团自主决策，确定性规则引擎让行为产生真实后果。

基于 LangGraph 的 Multi-Agent 协作：DM（地下城主）与多个 PC（玩家角色）共享一个 DND 风格的虚拟世界，每个 Tick 自动驱动情境创建、角色决策、行动执行与叙事生成，前端 Phaser.js 实时渲染 2D 瓦片地图与动画。

## 核心特性

- **LangGraph 状态图编排** — Tick 流水线将情境创建、数据加载、角色决策、行动执行、叙事生成、数据持久化编排为顺序 Graph 节点，3 个子图独立编译实现模块化拆分
- **Multi-Agent 协作** — DM Agent 负责情境创建与叙事生成，多个 PC Agent 各自运行决策-行动两阶段（decide → act），支持探索、对话、交互、战斗 4 种行动引擎
- **事件回放系统** — 后端 Tick 事件写入 DB，前端轮询拉取后按类型分发，驱动 Phaser.js 场景渲染与动画播放（地图切换、精灵移动、气泡对话、战斗特效），支持 1x~4x 倍速播放与页面刷新状态恢复
- **三层记忆架构** — 内存 deque 短期记忆、ChromaDB 语义检索 + SQLite 结构化过滤协同的长期记忆、独立反思记忆（LLM 生成高层次洞察），Scheduler 异步 Reflector 按定期/突发事件/累计阈值触发反思
- **多 Provider LLM 配置** — Provider/Purpose 分离的配置架构，支持多 LLM 提供商热切换，9 个 LLM Purpose 按温度与超时差异化配置，自动重试 + 模型降级 + Pydantic 结构化输出校验
- **Prompt 工程** — 全套 Jinja2 模板体系，动态注入世界观与场景上下文，统一语言约束；接入 Langfuse + LangSmith 实现 LLM 调用全链路追踪与成本核算

## 快速开始

### 环境要求

- Python 3.12+（推荐 [uv](https://github.com/astral-sh/uv) 管理）
- Node.js 20+
- LLM API Key（DeepSeek / GLM / Zen-Proxy 任选其一）

### 后端

```bash
cd backend
uv sync
cp ../.env.example ../.env  # 编辑 .env 填入 API Key
uv run uvicorn src.main:app --reload --port 8000
```

验证：访问 http://localhost:8000/health

### 前端

```bash
cd frontend
npm install
npm run dev  # 默认 http://localhost:3000
```

### Docker（可选）

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

### Mock 模式（无 API Key 也能跑）

`config.yaml` 中 `runtime.llm_mock: true` + `runtime.data_mode: "mock"` 即可纯离线运行，适合快速体验与开发调试。

## 项目结构

```
AIGameWorld/
├── backend/              # Python 后端
│   ├── src/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── cli.py            # aw CLI 命令
│   │   ├── graph/            # LangGraph 编排（Tick 流水线 + 子图）
│   │   ├── engine/           # 行动引擎（decision/talk/explore/interact/combat/reflection）
│   │   ├── services/         # 服务层（State ↔ Engine 胶水）
│   │   ├── repository/       # 数据访问层（SQLite + ChromaDB + Neo4j）
│   │   ├── prompts/          # Jinja2 Prompt 模板
│   │   ├── scheduler/        # 异步任务（Reflector 反思）
│   │   └── domain/           # Pydantic 领域模型
│   └── tests/                # 300+ pytest 用例
├── frontend/             # TypeScript 前端
│   ├── src/
│   │   ├── scenes/           # Phaser 场景（Boot/GameScene）
│   │   ├── managers/         # 业务控制器（EventManager/MovementManager）
│   │   ├── TickPlayer.ts     # Tick 播放器（状态机 + 轮询 + 事件分发）
│   │   └── ui/               # DOM 面板（控制栏/事件/叙事/角色）
│   └── tests/e2e/            # 38 个 Playwright E2E 测试
├── worlds/               # World Pack（世界观 YAML + 地图 TMX）
├── docker/               # Docker 配置
└── Makefile              # 顶层命令
```

## CLI 命令

后端提供 `aw` 交互式终端：

```bash
cd backend
uv run aw shell                    # 交互式 shell
aw> import worlds/forgotten_realms # 导入世界包
aw> run 3                          # 跑 3 个 tick
aw> llm on                         # 开启 LLM 模式
aw> exit

uv run aw serve                    # 一键启动前后端
uv run aw view                     # DB 查看器
```

## 测试

```bash
# 后端（300+ 用例）
cd backend && uv run pytest

# 前端 E2E（38 用例，自动启动后端 mock 环境）
cd frontend && npx playwright test
```

## 技术栈

**后端**：Python 3.12 / FastAPI / LangGraph / LangChain / ChromaDB / SQLite / Neo4j / Pydantic / uv
**前端**：TypeScript / Phaser 3 / Vite / Playwright
**LLM**：DeepSeek / GLM / Zen-Proxy（可切换）
**可观测性**：Langfuse / LangSmith
**工程化**：GitHub Actions CI / ruff / mypy / eslint / pytest / vitest

## License

MIT
