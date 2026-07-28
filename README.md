# AIGameWorld

> LLM 驱动的 Multi-Agent 游戏世界模拟引擎。DM Agent 创造情境，PC Agent 主角团自主决策，确定性规则引擎让行为产生真实后果。

基于 LangGraph 的 Multi-Agent 协作：DM（地下城主）与多个 PC（玩家角色）共享一个 DND 风格的虚拟世界，每个 Tick 自动驱动情境创建、角色决策、行动执行与叙事生成，前端 Phaser.js 实时渲染 2D 瓦片地图与动画。

## 核心特性

- **LangGraph 状态图编排** — 7 节点顺序流水线：dm_create → load_data → tick_init → pc_subgraph → flush_events → dm_narrate → persist_tick，3 个子图独立编译实现模块化拆分
- **Multi-Agent 协作** — DM Agent 负责情境创建与叙事生成，多个 PC Agent 各自运行决策-行动两阶段（decide → act），支持探索、对话、交互、战斗 4 种行动引擎
- **事件回放系统** — 后端 Tick 事件写入 DB，前端 HTTP 轮询拉取后按类型分发，驱动 Phaser.js 场景渲染与动画播放（地图切换、精灵移动、气泡对话、战斗特效），支持 1x~4x 倍速播放与页面刷新状态恢复
- **三层记忆架构** — 短期记忆（内存 deque，仅存不持久化）、长期记忆（ChromaDB 语义检索 + SQLite 补全，三要素精排）、反思记忆（LLM 生成高层次洞察，ChromaDB 独立集合），Scheduler 异步 Reflector 按定期/突发事件/累计阈值触发反思
- **多 Provider LLM 配置** — Provider/Purpose 分离的配置架构，支持 DeepSeek / GLM / Zen-Proxy 热切换，9 个 LLM Purpose 按温度与超时差异化配置，自动重试 + 模型降级 + Pydantic 结构化输出校验
- **Prompt 工程** — 全套 Jinja2 模板体系，动态注入世界观与场景上下文，统一语言约束；接入 Langfuse + LangSmith 实现 LLM 调用全链路追踪与成本核算
- **World Pack 系统** — YAML 驱动的世界包，支持世界观、角色、场景、物品、任务的声明式定义，启动时自动索引到 ChromaDB 知识库

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
uv run python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

验证：访问 http://localhost:8000/health

### 前端

```bash
cd frontend
npm install
npm run dev  # 默认 http://localhost:3000
```

浏览器访问 `http://localhost:3000/?pack=mock_world`

### Docker（可选）

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

### Mock 模式（无 API Key 也能跑）

`config.yaml` 中 `runtime.data_mode: "mock"` + `runtime.mock_dataset: "tavern"` 即可纯离线运行，适合快速体验与开发调试。

## 项目结构

```
AIGameWorld/
├── backend/                  # Python 后端
│   ├── src/
│   │   ├── server.py             # FastAPI 入口
│   │   ├── orchestrator.py       # Tick 编排器
│   │   ├── config.py             # 配置加载器（YAML + Pydantic）
│   │   ├── graph/                # LangGraph 编排（主图 + 3 子图）
│   │   │   ├── graph.py              # 主 Tick 流水线
│   │   │   ├── state.py              # OverallState / PcSubState
│   │   │   └── subgraphs/            # load_data / tick_init / pc 子图
│   │   ├── engine/               # 行动引擎（8 个子引擎）
│   │   │   ├── dm/                   # DM 情境创建 + 叙事
│   │   │   ├── decision/             # PC/Actor 决策引擎
│   │   │   ├── talk/                 # 对话引擎
│   │   │   ├── explore/              # 探索引擎
│   │   │   ├── interact/             # 交互引擎
│   │   │   ├── combat/               # 战斗引擎
│   │   │   ├── reflection/           # 反思引擎
│   │   │   └── quest/                # 任务引擎
│   │   ├── services/             # 服务层（9 个文件）
│   │   │   ├── dm_service.py         # DM 服务
│   │   │   ├── pc_service.py         # PC 决策/行动服务
│   │   │   ├── memory_service.py     # 记忆检索编排
│   │   │   ├── data_service.py       # 数据持久化
│   │   │   ├── event_service.py      # 事件构造
│   │   │   └── tick_init_service.py  # Tick 初始化
│   │   ├── repository/           # 数据访问层（11 个 Repo）
│   │   │   ├── memory_repo.py        # 记忆存取（短期+长期+反思）
│   │   │   ├── knowledge_repo.py     # World Pack 知识库
│   │   │   ├── neo4j_repo.py         # Neo4j 图数据库
│   │   │   └── ...                   # pc/actor/scene/item/event/world/dm_record
│   │   ├── storage/              # 存储层
│   │   │   ├── chroma_client.py      # ChromaDB 向量存储（BGE-M3）
│   │   │   └── sqlite_client.py      # SQLite 连接管理
│   │   ├── domain/               # Pydantic 领域模型（14 个文件）
│   │   ├── prompts/              # Jinja2 Prompt 模板
│   │   ├── scheduler/            # 异步任务（Reflector 反思）
│   │   ├── llm/                  # LLM 客户端 + Mock
│   │   └── utils/                # 工具模块（日志/追踪/辅助）
│   ├── tests/                    # 34 个测试文件（300+ 用例）
│   └── data/                     # SQLite + ChromaDB 数据
├── frontend/                 # TypeScript 前端
│   ├── src/
│   │   ├── main.ts               # 入口文件
│   │   ├── bootstrap.ts          # 启动引导（健康检查 + 世界加载）
│   │   ├── TickPlayer.ts         # Tick 播放器（状态机 + 轮询 + 事件分发）
│   │   ├── scenes/               # Phaser 场景（Boot/GameScene）
│   │   ├── managers/             # 业务控制器（EventManager/MovementManager）
│   │   ├── ui/                   # DOM 面板（控制栏/事件/叙事/角色/Mock配置/指标）
│   │   ├── state/                # 状态管理（WorldStore/TickStore）
│   │   └── client/               # HTTP API 客户端
│   └── tests/e2e/                # Playwright E2E 测试
├── world-pack/               # World Pack（世界观 YAML）
│   └── forgotten_realms/         # 示例世界包
├── docker/                   # Docker 配置
├── config.yaml               # 主配置文件
└── Makefile                  # 顶层命令
```

## 记忆系统

### 架构

```
┌──────────┬──────────────────┬─────────────────┐
│ 短期记忆  │ 长期记忆          │ 反思记忆         │
│ deque    │ ChromaDB + SQLite │ ChromaDB 独立集  │
│ 内存窗口  │ 语义检索 + 补全    │ LLM 抽象洞察     │
└──────────┴──────────────────┴─────────────────┘
```

### 检索策略

- **短期记忆**：deque 窗口全量注入，按 tick 倒序
- **反思记忆**：ChromaDB 语义检索全量注入，前置
- **长期记忆**：ChromaDB 语义召回（top_k×3）→ SQLite 补全字段 → 三要素精排取 top_k

### 三要素评分

`Score = Relevance(语义相似度) + Recency(指数时间衰减) + Importance(1-10归一化)`

### 重要性映射

| 记忆类型 | importance |
|----------|-----------|
| reflection | 10 |
| combat | 8 |
| interact | 4 |
| talk | 3 |
| explore | 2 |
| observation | 1 |

### 反思触发

- **周期触发**：每 50 tick
- **突发事件**：最新记忆 importance ≥ 8
- **累计触发**：SQLite SUM(importance) ≥ 100

## CLI 命令

后端提供 `aw` 交互式终端：

```bash
cd backend
uv run aw shell                    # 交互式 shell
aw> import world-pack/forgotten_realms  # 导入世界包
aw> run 3                          # 跑 3 个 tick
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

## 配置

`config.yaml` 关键配置项：

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `server.port` | 8000 | 后端 API 端口 |
| `runtime.data_mode` | mock | 数据模式：mock / real |
| `runtime.db_name` | data/dev.db | SQLite 数据库路径 |
| `runtime.mock_dataset` | tavern | Mock 数据集名 |
| `llm_provider` | deepseek | LLM 提供商 |
| `database.chroma_path` | data/chroma/ | ChromaDB 持久化路径 |
| `database.embedding_model` | bge-m3 | 嵌入模型 |
| `auto_run.reflection_interval` | 5 | 反思间隔（tick） |

## 技术栈

**后端**：Python 3.12 / FastAPI / LangGraph / LangChain / ChromaDB 1.5 / SQLite / Neo4j / Pydantic / uv

**前端**：TypeScript / Phaser 3 / Vite / Playwright

**LLM**：DeepSeek / GLM / Zen-Proxy（可切换）

**可观测性**：Langfuse / LangSmith

**工程化**：GitHub Actions CI / ruff / pyright / eslint / prettier / pytest / vitest

## License

MIT
