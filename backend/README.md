# AIGameWorld 后端 / Backend

DM 驱动的虚拟 DND 世界模拟引擎。FastAPI + LangGraph + SQLite + ChromaDB。

## 快速开始 / Quick Start

```bash
cd backend
uv sync                                    # 安装依赖 / Install dependencies
cp ../.env.example ../.env                 # 配置 API Key / Configure API key
uv run aw shell                            # 启动交互式终端 / Launch interactive shell
```

## CLI 命令 / CLI Commands

### 交互式 Shell / Interactive Shell

```bash
uv run aw shell                          # 默认 DB / Default DB
uv run aw shell --pack-id forgotten_realms  # 指定 pack / Specify pack
```

进入后支持以下命令：

| 命令 | 说明 |
|------|------|
| `import <dir>` | 导入 world-pack 到 DB（支持交互式输入路径） |
| `run [n]` | 运行 n 个 tick（默认 5，支持交互式输入） |
| `pack <id>` | 设置/查看当前 pack_id |
| `llm on\|off` | 开关 LLM 模式 |
| `db on\|off` | 开关 DB 读写 |
| `db-path <path>` | 设置 DB 文件路径 |
| `show` | 显示当前设置 + DB 统计 |
| `list` | 列出 DB 中所有已导入的 pack |
| `clear` | 清空运行时数据（events/narratives） |
| `help` / `?` | 显示帮助 |
| `exit` / `quit` | 退出 |

### 单次运行 / One-shot Run

```bash
uv run aw run --ticks 5                                        # 纯 mock，不写 DB
uv run aw run --ticks 3 --db                                   # DB 读写 + 种子数据
uv run aw run --ticks 3 --db --pack-id forgotten_realms         # 从 DB 加载 pack 数据
uv run aw run --ticks 3 --db --pack-id forgotten_realms --llm   # LLM + pack 数据
```

### 导入 Pack / Import Pack

```bash
uv run aw import worlds/forgotten_realms --db data/world_db.db
```

### 诊断测试 / Diagnostics

```bash
uv run aw test --all                    # 测试 LLMClient + DM Engine + Full Tick
uv run aw test --client                 # 仅测试 LLMClient
uv run aw test --engine                 # 仅测试 DM Engine
```

## 典型工作流 / Typical Workflow

```bash
# 1. 启动 shell
uv run aw shell

# 2. 导入世界
aw> import worlds/forgotten_realms

# 3. 查看状态
aw> show

# 4. 跑 3 个 tick
aw> run 3

# 5. 开 LLM 再跑
aw> llm on
aw> run 2

# 6. 清理退出
aw> clear
aw> exit
```

## 项目结构 / Project Structure

```
backend/
├── src/
│   ├── cli.py                # CLI 入口（aw 命令）
│   ├── main.py               # FastAPI 服务入口
│   ├── config.py             # 配置加载
│   ├── domain/               # Pydantic 领域模型
│   ├── engine/               # 业务逻辑（DM/Character/Combat/...）
│   ├── graph/                # LangGraph 编排（7 Phase TickGraph）
│   ├── llm/                  # LLM 客户端（DeepSeek/Claude）
│   ├── prompts/              # Jinja2 Prompt 模板
│   ├── repository/           # 数据访问层（SQLite + ChromaDB）
│   ├── rules/                # D20 规则引擎
│   ├── schemas/              # API Request/Response DTO
│   ├── services/             # 服务层（State ↔ Engine 胶水）
│   ├── storage/              # SQLite / ChromaDB 客户端
│   ├── utils/                # 工具函数
│   └── world_pack_loader/    # YAML Pack 加载器
├── tests/                    # 337 项测试
├── data/                     # 运行时数据（gitignore）
│   ├── world_db.db           # SQLite 数据库
│   └── chroma/               # ChromaDB 向量存储
├── pyproject.toml            # 项目配置 + aw 入口
└── README.md                 # 本文件
```

## 开发 / Development

```bash
uv run ruff check .           # Lint
uv run ruff format .          # Format
uv run pyright .              # 类型检查
uv run pytest                 # 运行测试（333 passed）
```

## 相关文档 / Related Docs

- [AIGameWorld 知识库](../../../multi-agent-manager/knowledge/domains/dev/AIGameWorld/)
- [架构方案](../../../multi-agent-manager/knowledge/domains/dev/AIGameWorld/docs/03-architecture.md)
- [路线图](../../../multi-agent-manager/knowledge/domains/dev/AIGameWorld/ROADMAP.md)
