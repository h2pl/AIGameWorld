# AIGameWorld 可观测性、RAG 增强、监控与评估体系架构

> 三层可观测性策略：(1) RAG 增强 (2) 双链路追踪（开发期 LangSmith + 生产期 Langfuse）(3) 三层评估（LangSmith 开发评估 + Langfuse 生产监控 + 自研 WorldStateEvaluator 游戏业务评估）
> 参考业界 2025-2026 最佳实践，结合项目现状给出可落地方案。

---

## 一、ChromaDB 现状与 RAG 增强

### 1.1 当前 ChromaDB 用途

ChromaDB 目前用于 **角色记忆系统的长期语义检索层**，构成三层记忆架构的"长期"部分：

| 层级 | 存储 | 用途 |
|------|------|------|
| 短期 | `deque(maxlen=10)` | 内存中最近 10 条观察，全量读取 |
| 中期 | SQLite `memories` 表 | 按角色/tick/类型/重要性过滤查询 |
| 长期 | ChromaDB `mem_{pc_id}` 集合 | 语义相似度 Top-K 检索 |
| 反思 | ChromaDB `reflect_{pc_id}` 集合 | 反思洞察的语义检索 |

**数据流**：
- **写入**：每次事件发生 → `MemoryRepo.store()` → 同时写入 deque + SQLite + ChromaDB
- **读取**：`MemoryService.retrieve_memories()` → 合并三层结果 → 按 `score_memory()` 排序 → 注入 prompt
- **Mock 模式**：跳过 ChromaDB 语义检索，只用本 tick 内存中的记忆

**ChromaDB 配置**：`PersistentClient`，路径 `data/chroma/`，使用 ChromaDB 内置 embedding（默认 all-MiniLM-L6-v2）。

### 1.2 当前 RAG 的局限性

1. **Embedding 模型不可控**：使用 ChromaDB 默认的 `all-MiniLM-L6-v2`，中文语义理解弱
2. **仅用于角色记忆**：World Pack 知识、场景描述、世界观设定等未入库
3. **检索-生成未解耦**：RAG 流程散落在 MemoryService 中，没有独立的 retriever/generator 分层
4. **无检索质量评估**：不知道检索到的记忆是否真的相关，无法度量检索精度
5. **chunk 策略固定**：每条记忆是一个整体，没有做切片和重叠

### 1.3 RAG 增强方案

#### Phase 1：Embedding 模型升级

| 方案 | 模型 | 中文能力 | 部署方式 | 成本 |
|------|------|----------|----------|------|
| A | BGE-M3 (BAAI) | 优秀 | 本地 ONNX/Transformers | 免费 |
| B | text-embedding-3-small (OpenAI) | 优秀 | API | $0.02/1M tokens |
| C | m3e-base | 良好 | 本地 | 免费 |

**推荐方案 A**：BGE-M3 是当前中文语义检索的最佳开源选择，支持多语言、多粒度、多功能，可通过 ChromaDB 的 `embedding_function` 参数集成。

```python
from chromadb.utils import embedding_functions
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-m3"
)
```

#### Phase 2：World Pack 知识库 RAG

当前 World Pack 数据（`forgotten_realms/` 等）只在启动时通过 `data_service.inject_mock_data()` 写入 SQLite，未被向量化。

**新增 RAG 场景**：

| 知识类型 | 集合名 | 检索时机 | 注入目标 |
|----------|--------|----------|----------|
| 世界观设定 | `worldpack_lore` | dm_create / dm_narrate | `_dm_system.jinja` |
| 场景描述 | `worldpack_scenes` | dm_create / pc_decision | 对应 prompt |
| NPC 背景故事 | `worldpack_characters` | talk / interact | 对应 prompt |
| 物品/道具信息 | `worldpack_items` | interact / explore | 对应 prompt |
| 任务线 | `worldpack_quests` | dm_create / pc_decision | 对应 prompt |

**实现方式**：
1. World Pack 加载时，对 `lore.yaml`、`characters.yaml` 等做 chunk + embed 写入 ChromaDB
2. 各 engine 在 render prompt 前调用 `retrieve_knowledge(query, top_k=3)` 获取相关片段
3. 在 prompt 模板中增加 `{% if world_knowledge %}相关知识：{{ world_knowledge }}{% endif %}` 区块

#### Phase 3：检索质量评估（与第四部分评估系统联动）

- **Context Precision**：检索到的片段中，与当前场景/行为相关的比例
- **Context Recall**：应该被检索到的知识，实际被检索到的比例
- **Faithfulness**：LLM 生成内容是否忠实于检索到的上下文

---

## 二、双链路追踪（Dual Tracing Strategy）

> 核心策略：**LangSmith 负责开发期深度调试，Langfuse 负责生产期运营监控**。
> 两者互补而非替代——LangSmith 深度集成 LangGraph 帮你把 Agent 做对，Langfuse OTel-native 帮你把 Agent 跑稳。

### 2.1 双追踪策略总览

| 维度 | LangSmith（开发期） | Langfuse（生产期） |
|------|---------------------|-------------------|
| **核心定位** | 帮你把 Agent **做对** | 帮你把 Agent **跑稳** |
| **Graph/Node 调试** | ✅ LangGraph 原生深度集成 | ⚠️ 支持，但非核心场景 |
| **Prompt 管理** | ✅ 版本管理、实验、Playground | ❌ 不支持 |
| **数据集管理** | ✅ 原生评估数据集、批量运行 | ❌ 不支持 |
| **回归测试** | ✅ Prompt/Model/Graph 变更后自动回归 | ❌ 不支持 |
| **LLM Judge** | ✅ 内置评估流程（开发阶段） | ⚠️ 支持，但更偏生产 |
| **Token/Cost 追踪** | ⚠️ 支持，但不如 Langfuse | ✅ 长期统计分析更强 |
| **Dashboard** | ⚠️ 开发调试视图 | ✅ 更强的生产监控面板 |
| **性能/延迟** | ⚠️ 开发期够用 | ✅ 更偏运维 P50/P95/P99 |
| **告警/分析** | ❌ 不支持 | ✅ 生产运营告警更强 |
| **部署方式** | SaaS | 自托管（数据不出境） |
| **采样策略** | 开发期全量 | 生产期按需采样 |

### 2.2 LangSmith：开发期深度调试

LangSmith 与 LangGraph 原生集成，是开发阶段的核心工具：

**核心能力**：
1. **LangGraph 深度集成**：直接在 LangSmith UI 中查看 Graph 执行路径、Node 输入输出、State 变化
2. **Prompt 管理**：`.jinja` 模板的版本管理、A/B 实验、在线 Playground 即时调试
3. **数据集管理**：原生评估数据集创建、管理、批量运行（与第八节评估系统联动）
4. **回归测试**：Prompt/Model/Graph 变更后自动运行评估套件，防止退化
5. **LLM Judge**：内置 LLM-as-Judge 评估流程，开发阶段快速验证生成质量

**接入方式**：

```python
import os
os.environ["LANGSMITH_API_KEY"] = "..."
os.environ["LANGSMITH_PROJECT"] = "aigameworld-dev"

# LangGraph 自动集成——无需额外代码，LangSmith 自动捕获 Graph 执行
config = {
    "configurable": {"thread_id": world_id},
}
result = await graph.ainvoke(state, config)
```

### 2.3 Langfuse：生产期运营监控

Langfuse 基于 OpenTelemetry，是生产阶段的核心工具：

**核心能力**：
1. **Token/Cost 追踪**：自动从 LLM 响应提取 token usage，按 model 计费，长期统计趋势分析
2. **Dashboard**：生产监控面板——按 tag/metadata 过滤、Daily/Monthly 聚合
3. **性能/延迟**：运维视角的 P50/P95/P99 延迟监控
4. **告警/分析**：生产异常告警、成本异常检测、预算超支预警

**接入方式**：

```python
from langfuse.callback import CallbackHandler

def create_langfuse_handler(tick: int, world_id: str) -> CallbackHandler:
    return CallbackHandler(
        trace_name=f"tick-{tick}",
        tags=[f"world:{world_id}", f"tick:{tick}"],
        metadata={"world_id": world_id, "tick": tick},
    )

config = {
    "configurable": {"thread_id": world_id},
    "callbacks": [create_langfuse_handler(tick, world_id)],
}
result = await graph.ainvoke(state, config)
```

### 2.4 Span 层级设计（两套系统共享）

```
Trace: tick-{tick}
├── Span: dm_service.dm_create
│   └── Generation: LLM call (model, tokens, latency)
├── Span: load_data_subgraph
│   ├── Span: load_pc_data
│   └── Span: load_scene_data
├── Span: tick_init_subgraph
├── Span: pc_subgraph
│   ├── Span: pc_{id}.decide
│   │   └── Generation: LLM call
│   ├── Span: pc_{id}.action (talk/explore/interact/combat)
│   │   └── Generation: LLM call
│   └── ...
├── Span: event_service.flush_events
├── Span: dm_service.dm_narrate
│   └── Generation: LLM call
├── Span: data_service.persist_tick
│   ├── Span: persist_pc_positions
│   └── Span: persist_events
└── Span: reflection_service.reflect
    └── Generation: LLM call (if triggered)
```

### 2.5 配置策略

```yaml
# config.yaml
observability:
  langsmith:
    enabled: true                       # 开发期始终启用
    project: "aigameworld-dev"
    sampling_rate: 1.0                  # 开发期全量采样

  langfuse:
    enabled: true                       # 生产期启用
    tracing_environment: "production"
    sampling_rate: 0.1                  # 生产期 10% 采样
    cost_tracking: true                 # 启用成本追踪
```

---

## 三、性能/业务/Token 成本监控

### 3.1 当前状态

| 监控类型 | 现状 | 差距 |
|----------|------|------|
| 性能监控 | `log_graph` 记录 node 耗时，`logging.performance: false` | 无聚合、无告警、无可视化 |
| 业务监控 | 无 | 不知道 tick 成功率、action 分布、角色行为统计 |
| Token 成本 | `_token_usage()` 从 LLM 响应提取，写入日志 | 无聚合、无计费、无预算控制 |

### 3.2 监控指标体系设计

#### 3.2.1 性能指标（RED 方法）

| 指标 | 采集方式 | 告警阈值 |
|------|----------|----------|
| Tick 处理延迟 P50/P95/P99 | Langfuse trace 耗时 | P99 > 60s |
| LLM 调用延迟（按 purpose 分） | Langfuse Generation latency | P95 > 20s |
| Graph 节点延迟分布 | Langfuse Span latency | 单节点 P95 > 15s |
| Tick 吞吐量（ticks/min） | 主动计算 | < 1 tick/min |
| 前端渲染延迟 | Performance API | 首屏 > 5s |

#### 3.2.2 业务指标

| 指标 | 采集方式 | 用途 |
|------|----------|------|
| Tick 成功率 | `data_service.persist_tick` 成功/失败计数 | 质量门禁 |
| Action 类型分布 | `events` 表按 type 统计 | 行为分析 |
| 角色决策多样性 | `pc_decision` 的 `action_type` 熵值 | 检测模式僵化 |
| DM 叙事长度分布 | `dm_narrative` 字段长度统计 | 质量波动预警 |
| 记忆检索命中率 | ChromaDB query 返回条数 / 请求次数 | RAG 效果 |
| 反思触发频率 | `reflection_service.reflect` 调用次数 | 自适应机制 |

#### 3.2.3 Token 成本指标（FinOps）

| 指标 | 采集方式 | 用途 |
|------|----------|------|
| Token 消耗总量（input/output） | Langfuse 自动采集 | 月度账单预测 |
| Token 消耗按 purpose 分布 | Langfuse metadata tag | 定位高消耗 purpose |
| Token 消耗按 tick 分布 | trace metadata | 单 tick 成本 |
| 单次对话/探索/战斗平均 Token | 聚合计算 | 单次交互成本 |
| 模型单价 × Token = 实际成本 | Langfuse 模型定价表 | 精确计费 |
| 成本趋势/异常检测 | 时序分析 | 预算超支预警 |

### 3.3 实施方案

#### 方案：Langfuse Dashboard + 自定义 Metrics

**Langfuse 原生能力**：
- 自动从 LLM 响应中提取 token usage
- 按模型计算成本（需配置模型定价）
- Dashboard 支持按 tag/metadata 过滤
- 支持 Daily/Monthly 聚合

**需要额外开发的**：

```python
# backend/src/utils/metrics.py
from dataclasses import dataclass, field
from collections import defaultdict
import time

@dataclass
class TickMetrics:
    tick: int
    world_id: str
    start_time: float = 0.0
    end_time: float = 0.0
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    events_count: int = 0
    action_types: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: list[str] = field(default_factory=list)

    @property
    def latency_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    @property
    def estimated_cost(self) -> float:
        """基于模型定价估算成本（DeepSeek Chat 为例）"""
        input_cost = self.tokens_in * 0.001 / 1_000_000   # $0.001/1M input
        output_cost = self.tokens_out * 0.002 / 1_000_000  # $0.002/1M output
        return input_cost + output_cost


class MetricsCollector:
    """轻量级指标收集器，写入 SQLite 供 Dashboard 查询"""

    def __init__(self, sqlite):
        self._sqlite = sqlite
        self._current: dict[str, TickMetrics] = {}  # world_id → TickMetrics

    def start_tick(self, world_id: str, tick: int) -> None:
        self._current[world_id] = TickMetrics(
            tick=tick, world_id=world_id, start_time=time.monotonic()
        )

    def record_llm(self, world_id: str, tokens_in: int, tokens_out: int) -> None:
        m = self._current.get(world_id)
        if m:
            m.llm_calls += 1
            m.tokens_in += tokens_in
            m.tokens_out += tokens_out

    async def finish_tick(self, world_id: str) -> TickMetrics | None:
        m = self._current.pop(world_id, None)
        if not m:
            return None
        m.end_time = time.monotonic()
        # 写入 SQLite
        await self._sqlite.execute(
            "INSERT INTO tick_metrics (tick, world_id, latency_ms, llm_calls, "
            "tokens_in, tokens_out, events_count, estimated_cost_usd) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (m.tick, m.world_id, m.latency_ms, m.llm_calls,
             m.tokens_in, m.tokens_out, m.events_count, m.estimated_cost),
        )
        await self._sqlite.commit()
        return m
```

#### API 端点暴露指标

```python
# backend/src/api/metrics.py
@router.get("/api/world/{world_id}/metrics")
async def get_metrics(world_id: str, range_hours: int = 24):
    """返回指定时间范围内的监控指标"""
    ...

@router.get("/api/world/{world_id}/metrics/cost")
async def get_cost_metrics(world_id: str):
    """返回 Token 成本统计"""
    ...
```

#### 前端 Dashboard 集成

在 ControlBar 或独立面板中展示关键指标：
- 当前 tick 延迟 + LLM 调用次数
- 累计 Token 消耗 + 估算成本
- Action 类型饼图

---

## 四、三层评估体系（Three-Layer Evaluation）

> 核心策略：**LangSmith 帮你把 Agent 做对，Langfuse 帮你把 Agent 跑稳，自研 Evaluator 帮你判断游戏世界是否符合业务规则**。
> 三层评估互补而非替代——分别覆盖开发、生产、业务三个不同维度。

### 4.1 三层评估架构

```
┌──────────────────────────────────────────────────────────────────────┐
│ Layer 3: 自研 WorldStateEvaluator                                    │
│ 帮你判断游戏世界是否符合业务规则                                        │
│ → DnD 规则一致性、NPC 行为、地图有效性、世界不变量                        │
│ → 通用平台无法替代，RPG 项目核心评估层                                    │
├──────────────────────────────────────────────────────────────────────┤
│ Layer 2: Langfuse（生产期）                                           │
│ 帮你把 Agent 跑稳（监控、成本、性能、运营）                               │
│ → Token/Cost Dashboard、延迟 P50/P95/P99、生产告警                     │
├──────────────────────────────────────────────────────────────────────┤
│ Layer 1: LangSmith（开发期）                                          │
│ 帮你把 Agent 做对（开发、评估、回归）                                    │
│ → Prompt 实验追踪、数据集管理 + 批量运行、内置 LLM-as-Judge、变更回归      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Layer 1：LangSmith — 帮你把 Agent 做对

LangSmith 是开发阶段的核心评估平台，深度集成 LangGraph 生态：

| 能力 | 说明 |
|------|------|
| **Prompt 实验追踪** | 每次 Prompt 变更自动记录，支持 A/B 对比 |
| **数据集管理 + 批量运行** | 原生评估数据集创建、管理、批量运行评估 |
| **内置 LLM-as-Judge** | 开发阶段快速验证 DM 叙事质量、PC 决策合理性 |
| **变更回归** | Prompt/Model/Graph 变更后自动回归评估，防止退化 |

**开发期评估流程**：
1. 在 LangSmith 中创建评估数据集（Golden Dataset）
2. 修改 Prompt/Graph 后，一键批量运行评估
3. 对比修改前后评分，确认是否改善
4. 连续低于阈值的维度自动生成失败报告

### 4.3 Layer 2：Langfuse — 帮你把 Agent 跑稳

Langfuse 是生产阶段的核心监控平台，专注运营稳定性：

| 能力 | 说明 |
|------|------|
| **Token/Cost Dashboard** | 按模型/按 purpose 统计 token 消耗和成本趋势 |
| **延迟 P50/P95/P99** | 运维视角的 Tick 延迟、LLM 调用延迟监控 |
| **生产告警** | 成本异常、延迟突增、错误率上升自动告警 |

**生产期监控重点**：
- 每个 tick 的 token 消耗和成本
- LLM 调用延迟是否在 SLA 内
- 错误率和重试率趋势

### 4.4 Layer 3：自研 WorldStateEvaluator — 帮你判断游戏世界是否符合业务规则

这是 RPG 项目最核心、也是任何通用平台都无法替代的评估层。详见**第八节**。

LangSmith 评估"Agent 是否正确"（输出质量、Prompt 效果），自研 Evaluator 评估"游戏世界是否合理"（规则一致性、世界不变量）。

---

## 五、实施路线图

| Phase | 内容 | 依赖 |
|-------|------|------|
| **P1** | LangSmith 追踪 + BGE-M3 embedding 升级 | LangSmith 项目配置 + 模型下载 |
| **P2** | Langfuse 生产监控 + MetricsCollector | P1 LangSmith + Langfuse 自托管部署 |
| **P3** | World Pack RAG + 自研 WorldStateEvaluator | P1 BGE-M3 + 游戏规则定义 |
| **P4** | 评估 Dashboard + Prompt 优化闭环 | P2 Langfuse + P3 Evaluator |

---

## 六、技术栈汇总

| 能力 | 工具 | 侧重点 |
|------|------|--------|
| 开发调试 + 评估 | LangSmith | 开发期：Graph 调试、Prompt 实验、回归评估 |
| 生产监控 + 成本 | Langfuse | 生产期：Token 成本、延迟、告警 |
| 游戏业务评估 | 自研 WorldStateEvaluator | RPG 特有：规则一致性、NPC 逻辑、地图有效性 |
| Embedding | BGE-M3 (BAAI) | 中文语义检索 |
| 向量存储 | ChromaDB | 本地 PersistentClient |
| 指标存储 | SQLite `tick_metrics` 表 | 复用现有 DB |

---

## 七、参考来源

- [LangSmith OpenTelemetry Integration](https://docs.langchain.com/langsmith/trace-with-opentelemetry)
- [Instrument an AI Agent: LangSmith, Langfuse, OTel GenAI (2026)](https://www.bestaiweb.ai/how-to-instrument-an-ai-agent-with-langsmith-langfuse-and-opentelemetry-genai-in-2026/)
- [Agent Observability and Production Debugging (2026)](https://zylos.ai/research/2026-04-29-agent-observability-production-debugging/)
- [RAG 评估终极指南 — LLM-as-Judge 新范式](https://blog.csdn.net/liu1983robin/article/details/158545105)
- [RAGAS: How to Align an LLM as a Judge](https://docs.ragas.io/en/v0.4.1/howtos/applications/align-llm-as-judge/)
- [RAG Evaluation Guide: Metrics, Frameworks & LLM Evaluation in Production](https://au1206.github.io/posts/rag-evaluation-guide/)
- [Best LLM Evaluation Frameworks in 2026](https://futureagi.com/blog/llm-evaluation-frameworks-metrics-best-practices/)
- [Tracking LLM Token Usage Across Providers (Portkey)](https://portkey.ai/blog/tracking-llm-token-usage-across-providers-teams-and-workloads/)
- [LLM Observability Best Practices (Maxim AI)](https://www.getmaxim.ai/articles/llm-observability-best-practices-for-2025)

---

## 八、自研 World State Evaluator

> 通用 LLM 评估平台无法理解游戏世界的业务规则。这一层是 RPG 项目最核心、
> 也是任何通用平台都无法替代的评估能力。

### 8.1 设计理念

一句话总结：
- LangSmith 帮你把 Agent **做对**（开发、评估、回归）
- Langfuse 帮你把 Agent **跑稳**（监控、成本、性能、运营）
- 自研 Evaluator 帮你判断**游戏世界是否符合业务规则**

### 8.2 评估维度

| 维度 | 检查内容 | 实现方式 | 严重级别 |
|------|----------|----------|----------|
| 规则一致性 | DnD 规则执行是否正确（伤害计算、技能检定） | 确定性断言 | P0 Critical |
| NPC 行为一致性 | NPC 行为是否符合性格设定和记忆 | LLM-as-Judge | P1 High |
| 地图空间有效性 | PC/Actor 坐标是否在合法范围内 | 确定性断言 | P0 Critical |
| 任务因果一致性 | 事件之间是否有因果逻辑 | LLM-as-Judge | P1 High |
| 世界状态不变量 | 活着的NPC不会消失、物品不重复 | 确定性断言 | P0 Critical |
| 叙事连贯性 | DM叙事是否前后衔接 | LLM-as-Judge | P2 Medium |
| 角色决策合理性 | PC决策是否符合角色状态和情境 | LLM-as-Judge | P2 Medium |

### 8.3 确定性规则检查（每 tick 自动运行）

```python
class WorldStateEvaluator:
    """游戏世界状态评估器 / Game world state evaluator."""

    def evaluate(self, state: OverallState, events: list[TickEvent]) -> EvalReport:
        # P0: 地图空间有效性
        self._check_positions(state)
        # P0: 世界状态不变量
        self._check_invariants(state, events)
        # P0: DnD规则一致性
        self._check_combat_rules(events)
        # P1: 任务因果性
        self._check_event_causality(events)
        return self._report
```

### 8.4 LLM-as-Judge 规则（评估套件运行时）

使用独立模型评估 NPC 行为一致性和叙事连贯性，
与 LangSmith 的评估互补——LangSmith 评估"Agent 是否正确"，
自研 Evaluator 评估"游戏世界是否合理"。
