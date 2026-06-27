# AIGameWorld

> DM 驱动的虚拟 DND 世界模拟。DM 创造情境，主角团推动剧情，确定性规则让行为有真实后果。

## 快速开始

### 后端

```bash
cd backend
uv sync
cp ../.env.example ../.env  # 编辑 .env 填入 DEEPSEEK_API_KEY
uv run uvicorn src.main:app --reload --port 8000
```

访问 http://localhost:8000/health 验证。

### 前端

```bash
cd frontend
npm install
npx vite --port 3000
```

访问 http://localhost:3000 查看 Phaser 画布。

### Docker

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

## 项目结构

```
AIGameWorld/
├── backend/     # Python 后端 (FastAPI + LangGraph)
├── frontend/    # TypeScript 前端 (Phaser 3)
├── worlds/      # World Pack 目录
├── data/        # 运行时数据 (gitignore)
├── docker/      # Docker 配置
└── Makefile     # 顶层命令
```

## 文档

完整文档在 `knowledge/domains/dev/AIGameWorld/` 知识库中：
- README.md — 项目文档入口
- PRD_最新版.md — 产品需求
- 架构方案最新版.md — 架构设计
- docs/ — 分层设计
- engineering/ — 工程化规范
