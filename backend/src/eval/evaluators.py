"""Prompt 评估器 / Prompt evaluators for LangSmith evaluate().

评估维度 / Evaluation dimensions:
    - format: JSON 格式 + 字段完整性
    - quality: LLM-as-Judge 评估内容质量
    - constraint: 业务约束（如 hints 数量、action_type 有效性）
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.schemas.llm_output import DMOutput, PCDecideSchema

# ============================================================================
# 工具函数 / Utility functions
# ============================================================================


def _parse_output(run_output: Any) -> dict | None:
    """从 run.outputs 中提取解析后的 dict / Extract parsed dict from run.outputs."""
    if not run_output:
        return None
    result = run_output.get("result", run_output)
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None
    if isinstance(result, dict):
        return result
    # 尝试从对象的 model_dump 获取 / Try model_dump
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return None


def _get_messages(run_inputs: dict) -> str:
    """从 run.inputs 中提取 messages 文本 / Extract messages text from run.inputs."""
    messages = run_inputs.get("messages", [])
    parts = []
    for msg in messages:
        if isinstance(msg, list):
            for m in msg:
                role = m.get("type", m.get("role", "unknown"))
                content = m.get("content", "")
                parts.append(f"[{role}] {content}")
        elif isinstance(msg, dict):
            role = msg.get("type", msg.get("role", "unknown"))
            content = msg.get("content", "")
            parts.append(f"[{role}] {content}")
    return "\n".join(parts)


# ============================================================================
# 通用评估器 / Generic evaluators
# ============================================================================


def make_format_evaluator(purpose: str):
    """创建格式评估器（通过闭包绑定 purpose）/ Create format evaluator with purpose binding."""

    def evaluator(run, example) -> dict:
        """评估输出是否符合 JSON 格式和 schema / Evaluate JSON format and schema compliance."""
        output = _parse_output(run.outputs)
        if output is None:
            return {"key": "format", "score": 0.0, "comment": "输出不是有效 JSON"}

        schema_map = {"dm_create": DMOutput, "pc_decision": PCDecideSchema}
        schema = schema_map.get(purpose)

        if schema is None:
            return {"key": "format", "score": 0.5, "comment": f"未知 purpose: {purpose}"}

        try:
            schema(**output)
            return {"key": "format", "score": 1.0, "comment": "格式正确"}
        except Exception as e:
            return {"key": "format", "score": 0.3, "comment": f"schema 验证失败: {e}"}

    return evaluator


# ============================================================================
# dm_create 评估器 / dm_create evaluators
# ============================================================================


def dm_create_constraints_evaluator(run, example) -> dict:
    """评估 dm_create 的业务约束 / Evaluate dm_create business constraints.

    约束:
        - hints: 2-4 条
        - plot_brief: 非空
        - scene_id: 非空
    """
    output = _parse_output(run.outputs)
    if output is None:
        return {"key": "constraints", "score": 0.0, "comment": "无法解析输出"}

    hints = output.get("hints", [])
    plot_brief = output.get("plot_brief", "")
    scene_id = output.get("scene_id", "")

    issues = []
    if not isinstance(hints, list):
        issues.append("hints 不是列表")
    elif len(hints) < 2:
        issues.append(f"hints 数量不足（{len(hints)} < 2）")
    elif len(hints) > 4:
        issues.append(f"hints 数量过多（{len(hints)} > 4）")

    if not plot_brief:
        issues.append("plot_brief 为空")
    if not scene_id:
        issues.append("scene_id 为空")

    if not issues:
        return {"key": "constraints", "score": 1.0, "comment": "约束全部满足"}
    return {"key": "constraints", "score": 0.4, "comment": "; ".join(issues)}


def _extract_json(content: str) -> dict | None:
    """从 LLM 输出中提取 JSON（处理 markdown 代码块）/ Extract JSON from LLM output."""
    import re

    # 去除 markdown 代码块标记 / Strip markdown code blocks
    cleaned = re.sub(r"```(?:json)?\s*", "", content)
    cleaned = cleaned.replace("```", "").strip()

    # 尝试直接解析 / Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 尝试提取第一个 {...} 块 / Try to extract first {...} block
    match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def make_dm_create_quality_evaluator(judge_llm: BaseChatModel):
    """创建 dm_create 质量评估器（LLM-as-Judge）/ Create quality evaluator with LLM judge."""

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是一个 RPG 场景设计专家。请评估 DM 创造的场景质量。

评分维度（每项 0-1 分，取平均）：
1. hints 感官丰富度：是否包含视觉、听觉、嗅觉等具体感官描述
2. plot_brief 画面感：是否有具体场景画面，营造氛围
3. 场景一致性：hints 和 plot_brief 是否描述同一场景
4. 中文质量：是否使用简体中文，语言是否流畅自然

只输出一个 JSON，不要任何其他内容：{{"score": 0.85, "reason": "简短说明"}}""",
            ),
            ("human", "场景输出：\n{output}\n\n请评估。"),
        ]
    )

    chain = prompt | judge_llm

    def evaluator(run, example) -> dict:
        output = _parse_output(run.outputs)
        if output is None:
            return {"key": "quality", "score": 0.0, "comment": "无法解析输出"}

        try:
            result = chain.invoke({"output": json.dumps(output, ensure_ascii=False)})
            content = result.content if hasattr(result, "content") else str(result)
            parsed = _extract_json(content)
            if parsed is not None:
                return {
                    "key": "quality",
                    "score": float(parsed.get("score", 0.5)),
                    "comment": parsed.get("reason", ""),
                }
            # 解析失败时返回原始输出用于调试 / Return raw output for debugging
            return {
                "key": "quality",
                "score": 0.5,
                "comment": f"Judge 输出解析失败: {content[:200]}",
            }
        except Exception as e:
            return {"key": "quality", "score": 0.5, "comment": f"Judge 调用失败: {e}"}

    return evaluator


# ============================================================================
# pc_decision 评估器 / pc_decision evaluators
# ============================================================================


def pc_decision_constraints_evaluator(run, example) -> dict:
    """评估 pc_decision 的业务约束 / Evaluate pc_decision business constraints.

    约束:
        - action_type: talk/interact/combat/explore/wait 之一
        - target_id/target_type: 根据 action_type 匹配
        - thought: 非空，2-4 句
    """
    output = _parse_output(run.outputs)
    if output is None:
        return {"key": "constraints", "score": 0.0, "comment": "无法解析输出"}

    action = output.get("action", output)
    action_type = action.get("action_type", "")
    target_id = action.get("target_id")
    target_type = action.get("target_type")
    thought = action.get("thought", "")

    valid_types = {"talk", "interact", "combat", "explore", "wait"}
    issues = []

    if action_type not in valid_types:
        issues.append(f"action_type 无效: {action_type}")

    # action_type 与 target 匹配验证 / Validate action_type-target pairing
    if action_type in ("talk", "interact", "combat"):
        if not target_id:
            issues.append(f"{action_type} 需要 target_id")
        if not target_type:
            issues.append(f"{action_type} 需要 target_type")
    elif action_type in ("explore", "wait"):
        if target_id is not None:
            issues.append(f"{action_type} 的 target_id 应为 null")
        if target_type is not None:
            issues.append(f"{action_type} 的 target_type 应为 null")

    if not thought:
        issues.append("thought 为空")

    if not issues:
        return {"key": "constraints", "score": 1.0, "comment": "约束全部满足"}
    return {"key": "constraints", "score": 0.4, "comment": "; ".join(issues)}


def make_pc_decision_quality_evaluator(judge_llm: BaseChatModel):
    """创建 pc_decision 质量评估器（LLM-as-Judge）/ Create quality evaluator with LLM judge."""

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是一个 RPG 决策设计专家。请评估 PC 决策的质量。

评分维度（每项 0-1 分，取平均）：
1. 决策合理性：行动是否契合当前情境和角色身份
2. thought 深度：是否有完整观察→联想→权衡→决定的思考链
3. 目标匹配：target_id 是否合理（talk 的对象是否有信息可提供等）
4. 中文质量：是否使用简体中文，语言是否流畅自然

只输出一个 JSON：{{"score": 0.85, "reason": "简短说明"}}""",
            ),
            ("human", "决策输出：\n{output}\n\n上下文：\n{context}\n\n请评估。"),
        ]
    )

    chain = prompt | judge_llm

    def evaluator(run, example) -> dict:
        output = _parse_output(run.outputs)
        if output is None:
            return {"key": "quality", "score": 0.0, "comment": "无法解析输出"}

        context = _get_messages(example.inputs)
        try:
            result = chain.invoke(
                {
                    "output": json.dumps(output, ensure_ascii=False),
                    "context": context[:2000],  # 截断防止超长 / Truncate
                }
            )
            content = result.content if hasattr(result, "content") else str(result)
            parsed = _extract_json(content)
            if parsed is not None:
                return {
                    "key": "quality",
                    "score": float(parsed.get("score", 0.5)),
                    "comment": parsed.get("reason", ""),
                }
            return {
                "key": "quality",
                "score": 0.5,
                "comment": f"Judge 输出解析失败: {content[:200]}",
            }
        except Exception as e:
            return {"key": "quality", "score": 0.5, "comment": f"Judge 调用失败: {e}"}

    return evaluator


# ============================================================================
# 评估器集合 / Evaluator collections
# ============================================================================


def get_evaluators(purpose: str, judge_llm: BaseChatModel | None = None) -> list:
    """获取指定 purpose 的评估器列表 / Get evaluators for a given purpose.

    Args:
        purpose: dm_create / pc_decision
        judge_llm: 用于 LLM-as-Judge 的模型（可选，不传则跳过质量评估）

    Returns:
        评估器函数列表
    """
    evaluators = [make_format_evaluator(purpose)]

    if purpose == "dm_create":
        evaluators.append(dm_create_constraints_evaluator)
        if judge_llm:
            evaluators.append(make_dm_create_quality_evaluator(judge_llm))
    elif purpose == "pc_decision":
        evaluators.append(pc_decision_constraints_evaluator)
        if judge_llm:
            evaluators.append(make_pc_decision_quality_evaluator(judge_llm))

    return evaluators
