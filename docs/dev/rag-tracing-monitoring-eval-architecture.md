# AIGameWorld 可观测性、RAG 增强、监控与评估体系架构

> 涵盖四大方向：(1) RAG 增强与 ChromaDB 深化应用 (2) 全链路追踪 (3) 性能/业务/Token 成本监控 (4) LLM 评估系统
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

## 二、全链路追踪（Distributed Tracing）

### 2.1 当前状态

| 组件 | 现状 | 差距 |
|------|------|------|
| LangGraph 回调 | `TickGraphCallback(BaseCallbackHandler)` 记录 node 延迟 + LLM token | 仅写日志，无 trace 链路 |
| 日志系统 | `utils/logging.py` 分层日志（api/graph/service/engine/repo） | 无 span 关联、无 trace_id |
| Langfuse | config.yaml 有配置项但 `enabled: false` | 未接入 |
| 前端 | 无任何 trace 传播 | 前后端链路断裂 |

**核心差距**：当前只有"日志"，没有"链路"——无法将一个 tick 的完整流程（API 请求 → Graph 节点 → LLM 调用 → 事件处理 → 前端渲染）串成一条可追踪的链路。

### 2.2 业界方案对比

| 方案 | 特点 | 与 LangGraph 集成 | 开源 | 适合场景 |
|------|------|-------------------|------|----------|
| **Langfuse** | OTel-native、`@observe` 装饰器、自托管 | 官方集成 | 是 | 需要 OTel 标准 + 数据主权 |
| **LangSmith** | LangChain/LangGraph 深度集成 | 原生 | 否（SaaS） | 纯 LangChain 技术栈 |
| **Arize Phoenix** | 开源、OTel、内建评估 | 社区集成 | 是 | 需要评估+追踪一体化 |
| **OTel + Jaeger/Grafana** | 厂商中立、标准协议 | 需手动埋点 | 是 | 已有 Grafana 体系 |

### 2.3 推荐方案：Langfuse（自托管）

**选择理由**：
1. **OTel-native**：Langfuse SDK v3+ 基于 OpenTelemetry，与 OTel GenAI semconv 1.29+ 对齐
2. **LangGraph 原生集成**：Langfuse 官方提供 `CallbackHandler`，直接注入 `config["callbacks"]`
3. **自托管**：项目已有 `LANGFUSE_BASE_URL=http://localhost:3000`，数据不出境
4. **评估集成**：Langfuse 内建 LLM-as-Judge 评估，可在 trace 基础上直接评分
5. **Token 成本追踪**：自动从 LLM 响应中提取 token usage，按 model 计费

### 2.4 实施方案

#### Step 1：启用 Langfuse 基础追踪

```python
# backend/src/utils/tracing.py
from langfuse.callback import CallbackHandler

def create_langfuse_handler(tick: int, world_id: str) -> CallbackHandler:
    return CallbackHandler(
        trace_name=f"tick-{tick}",
        tags=[f"world:{world_id}", f"tick:{tick}"],
        metadata={"world_id": world_id, "tick": tick},
    )
```

```python
# 在 graph.invoke 中注入
config = {
    "configurable": {"thread_id": world_id},
    "callbacks": [create_langfuse_handler(tick, world_id)],
}
result = await graph.ainvoke(state, config)
```

#### Step 2：Span 层级设计

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

#### Step 3：前端链路传播

在前端 API 请求头中注入 `trace_id`：

```typescript
// frontend/src/api/client.ts
async function fetchWithTrace(url: string, options?: RequestInit) {
  const traceId = crypto.randomUUID();
  return fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
      "X-Trace-Id": traceId,
    },
  });
}
```

后端 FastAPI 中间件提取并传播：

```python
@app.middleware("http")
async def trace_middleware(request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response
```

#### Step 4：配置生效

```yaml
# config.yaml
observability:
  langfuse:
    enabled: true                    # 改为 true
    tracing_environment: "development"
    sampling_rate: 1.0               # 开发环境全量采样
    cost_tracking: true              # 启用成本追踪
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

## 四、LLM 评估系统

### 4.1 当前状态

| 组件 | 现状 | 差距 |
|------|------|------|
| 回归测试 | `test_prompt_regression.py` + `test_character_prompts.py` | 只检查输出 JSON 格式，不评估内容质量 |
| 反思系统 | `reflection_engine.py` + `reflect_pc.jinja` | 有自反思机制但无外部评估 |
| 输出 Schema | `schemas/llm_output.py` 定义了结构 | 只验证结构不验证语义 |

### 4.2 评估框架对比

| 框架 | 特点 | 集成难度 | 适合场景 |
|------|------|----------|----------|
| **RAGAS** | RAG 四指标（Faithfulness/Context Precision/Context Recall/Answer Relevancy）+ LLM-as-Judge | 中 | RAG 检索质量评估 |
| **DeepEval** | PyTest 风格、20+ 内置指标、CI/CD 友好 | 低 | 回归测试中内嵌质量评估 |
| **LangSmith Evals** | 与 LangChain 生态深度集成、支持数据集管理 | 低 | 已用 LangSmith 追踪时 |
| **Arize Phoenix** | 开源、OTel 原生、评估+追踪一体 | 中 | 需要开源+自托管 |

### 4.3 推荐方案：DeepEval + RAGAS 组合

**选择理由**：
1. **DeepEval**：PyTest 风格，可嵌入现有 `backend/tests/` 体系，CI/CD 友好
2. **RAGAS**：专注 RAG 评估，与 ChromaDB 记忆检索评估天然契合
3. 两者都支持 **LLM-as-Judge** 模式，可用独立模型评估生成质量

### 4.4 评估维度设计

#### 按生成阶段评估

| 阶段 | 评估维度 | 评估方法 | 指标 |
|------|----------|----------|------|
| DM 创建情境 | 剧情合理性、与世界观一致性 | LLM-as-Judge | Correctness 1-5, Consistency 1-5 |
| DM 叙事 | 叙事连贯性、与上文衔接 | LLM-as-Judge + 语义相似度 | Faithfulness, Narrative Coherence |
| PC 决策 | 决策合理性、角色性格一致性 | LLM-as-Judge | Decision Rationality 1-5 |
| 对话 | 对话自然度、角色口吻一致性 | LLM-as-Judge | Dialogue Quality 1-5 |
| 探索/交互 | 探索描述丰富度、环境一致性 | LLM-as-Judge | Description Richness 1-5 |
| 战斗 | 战斗逻辑合理性、结果可信度 | LLM-as-Judge | Combat Logic 1-5 |
| 记忆检索 | 检索相关性、覆盖度 | RAGAS | Context Precision, Context Recall |
| 反思 | 反思深度、行为改善建议质量 | LLM-as-Judge | Reflection Depth 1-5 |

#### 按评估层次

```
┌─────────────────────────────────────────┐
│ L3: 人工评估（Golden Dataset + 人工标注）│  ← 季度/版本发布
├─────────────────────────────────────────┤
│ L2: LLM-as-Judge（自动评估）            │  ← 每日/每次 prompt 变更
├─────────────────────────────────────────┤
│ L1: 确定性检查（格式/Schema/长度）       │  ← 每次 CI
└─────────────────────────────────────────┘
```

### 4.5 实施方案

#### Step 1：构建 Golden Dataset

```yaml
# backend/evals/golden_dataset/dm_create.yaml
- tick: 1
  scene: "酒馆"
  pcs: ["战士艾瑞克", "法师米娅"]
  expected_elements:
    - 应提及酒馆环境
    - 应为角色设定初始目标
    - 不应出现与场景无关的事件
  quality_score: 5  # 人工标注
```

```yaml
# backend/evals/golden_dataset/narrative_coherence.yaml
- tick_pair: [1, 2]
  tick_1_narrative: "艾瑞克在酒馆听到关于地下城的传闻..."
  tick_2_narrative: "艾瑞克决定前往地下城探索..."
  expected: "tick 2 应自然衔接 tick 1 的事件"
  coherence_score: 4
```

#### Step 2：DeepEval 集成

```python
# backend/tests/eval/test_dm_quality.py
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval

# 定义评估指标
narrative_coherence_metric = GEval(
    name="Narrative Coherence",
    criteria="""评估叙事文本是否：
    1. 与上一轮叙事自然衔接
    2. 角色行为符合其性格设定
    3. 情节发展逻辑合理
    4. 无矛盾或突兀转折""",
    evaluation_params=["input", "actual_output"],
)

def test_dm_narrative_coherence():
    test_case = LLMTestCase(
        input=prev_narrative,
        actual_output=current_narrative,
        context=[scene_description, character_profiles],
    )
    assert_test(test_case, [narrative_coherence_metric])
```

#### Step 3：RAGAS 记忆检索评估

```python
# backend/tests/eval/test_memory_rag.py
from ragas import evaluate
from ragas.metrics import context_precision, context_recall, faithfulness
from datasets import Dataset

def test_memory_retrieval_quality():
    """评估 ChromaDB 记忆检索质量"""
    data = {
        "question": [query_for_each_tick],
        "contexts": [retrieved_memories_for_each_tick],
        "answer": [llm_generated_narrative],
        "ground_truth": [expected_relevant_memories],
    }
    dataset = Dataset.from_dict(data)
    result = evaluate(dataset, metrics=[context_precision, context_recall, faithfulness])
    # 断言质量门槛
    assert result["context_precision"] >= 0.7
    assert result["faithfulness"] >= 0.8
```

#### Step 4：评估驱动的 Prompt 优化闭环

```
评估结果 → 定位低分维度 → 分析失败 case → 修改 prompt 模板 → 重新评估 → 确认提升
     ↑                                                                  │
     └────────────── 回归验证 ←──────────────────────────────────────────┘
```

**具体流程**：
1. 每次修改 `.jinja` 模板后，自动运行评估套件
2. 对比修改前后评分，确认是否改善
3. 如果某个维度连续 3 次低于阈值（如 Faithfulness < 0.7），自动生成失败报告
4. 失败报告包含：低分 case → LLM 分析原因 → 建议改进方向

#### Step 5：评估 API 与 Dashboard

```python
# backend/src/api/eval.py
@router.post("/api/eval/run")
async def run_evaluation(world_id: str, dimensions: list[str]):
    """触发评估并返回结果"""
    ...

@router.get("/api/eval/results")
async def get_eval_results(world_id: str, last_n: int = 10):
    """获取最近 N 次评估结果趋势"""
    ...
```

---

## 五、实施路线图

| Phase | 内容 | 预计工期 | 依赖 |
|-------|------|----------|------|
| **P1** | 启用 Langfuse 追踪 + Token 成本统计 | 1 周 | Langfuse 自托管部署 |
| **P1** | Embedding 模型升级为 BGE-M3 | 3 天 | 模型下载 + ChromaDB 迁移 |
| **P2** | TickMetrics 收集器 + 成本 Dashboard | 1 周 | P1 Langfuse |
| **P2** | Golden Dataset 构建 + DeepEval 集成 | 1 周 | 人工标注 |
| **P3** | World Pack 知识库 RAG | 1 周 | P1 BGE-M3 |
| **P3** | RAGAS 记忆检索评估 | 1 周 | P2 DeepEval + P3 RAG |
| **P4** | 前端 trace 传播 + 评估 Dashboard | 1 周 | P1 + P2 |
| **P4** | 评估驱动 Prompt 优化闭环 | 持续 | P2 + P3 |

---

## 六、技术栈汇总

| 能力 | 技术选型 | 版本要求 | 部署方式 |
|------|----------|----------|----------|
| 链路追踪 | Langfuse SDK v3+ | Python ≥ 3.10 | Docker 自托管 |
| 链路标准 | OpenTelemetry GenAI semconv | 1.29+ | 嵌入应用 |
| Embedding | BGE-M3 (BAAI) | 最新 | 本地 Transformers |
| 向量存储 | ChromaDB | ≥ 0.4 | 本地 PersistentClient |
| LLM 评估 | DeepEval | ≥ 1.0 | pip install + CI |
| RAG 评估 | RAGAS | ≥ 0.4 | pip install + CI |
| 成本追踪 | Langfuse + 自定义 MetricsCollector | — | 嵌入应用 |
| 指标存储 | SQLite `tick_metrics` 表 | — | 复用现有 DB |
| 可视化 | Langfuse Dashboard + 前端面板 | — | — |

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
