# S5 — Character Reflection（角色反思）

## 目标

接通 reflection + summarizer 的 LLM 调用，实现条件触发的角色反思与记忆压缩。

## 触发条件

- PC：短期记忆重要性累计 >= 100
- Actor：短期记忆重要性累计 >= 200
- 检查时机：tick % reflection_interval == 0（默认每 5 tick）

## 输入/输出

| 阶段 | 输入 | 输出 |
|------|------|------|
| reflect | character profile + arc + 近期记忆(5条) + 历史反思(3条) | insight（洞见文本） |
| summarize | 所有角色近期事件(1 tick) | 压缩摘要 |

## 角色差异

| 维度 | PC 深度反思 | Actor 浅层反思 |
|------|------------|---------------|
| Prompt | 角色弧线分析 + 价值观一致性 | 行为模式总结 |
| 洞见长度 | 2-3 句 | 1 句 |
| importance | 10 | 5 |

## 实现步骤

1. **Schema 更新**——`ReflectionRequest` 加 `character_name`/`character_type`/`arc_stage`，`SummarizerRequest` 加 `config`
2. **Prompt 模板**——`reflect_pc.jinja` + `reflect_actor.jinja` + `summarize.jinja`
3. **Engine**——`reflect` + `summarize` 异步化，接入 LLM，带降级
4. **Service**——异步化，遍历角色 + 阈值检查 + importance 归零
5. **Subgraph**——保持不变（需 adapter 层处理多角色迭代）

## 护栏

- 反射输出非空校验
- 角色名必须在输出中出现
- LLM 失败降级为空 insight（不抛异常）

## 验证标准

- PC 重要性 >= 100 触发深度反思，Actor >= 200 触发浅层反思
- 反思后 importance_accumulator 归零
- LLM 失败时降级输出不阻塞其他角色
- summarizer 压缩后 context token 减少
