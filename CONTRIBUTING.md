# Contributing to AIGameWorld

## 开发流程 / Development Process

1. 阅读 [docs/01-overview.md] 了解文档体系
2. 找到 [ROADMAP.md] 中当前里程碑
3. 按 [docs/07-skill-usage-guide.md] 使用 agent-toolkit skill 驱动开发
4. TDD: 先写测试再写实现

## 提交规范 / Commit Convention

```
type(scope): subject

提交末尾须署名:
--- {Agent名} ({模型名})
```

类型: feat | fix | docs | chore | refactor | test | audit | rule | memory

## 提交前检查 / Pre-commit

```bash
make precommit
```

自动检查: 密钥 → 注释率 → ruff → prettier → pytest → vitest

## 注释规则 / Comment Rules

所有文件必须有中英双语注释，不限类型。格式: `# 中文 / English`

## 变更联动 / Change Propagation

改一处必须同步所有关联处。详见 RULE.md §变更联动。

---

--- CodeBuddy (DeepSeek-V4-Pro)
