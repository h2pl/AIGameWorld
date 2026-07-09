"""LLM 评估引擎 / LLM Evaluation Engine.

基于 DeepEval 实现三层评估体系：
- L1 确定性检查（格式/Schema/长度）
- L2 LLM-as-Judge（叙事连贯性、决策合理性等）
- L3 人工评估（Golden Dataset + 人工标注）
"""

import json
from pathlib import Path
from typing import Any

import yaml

from src.utils.logging import get_logger

logger = get_logger(__name__)

_GOLDEN_DIR = Path(__file__).parent / "golden_dataset"


def load_golden_dataset(name: str) -> list[dict[str, Any]]:
    """加载 Golden Dataset YAML / Load golden dataset YAML."""
    path = _GOLDEN_DIR / f"{name}.yaml"
    if not path.exists():
        logger.warning("[eval] golden dataset not found: %s", path)
        return []
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


# ── L1 确定性检查 / L1 Deterministic checks ──


def check_json_schema(output: str, required_fields: list[str]) -> dict[str, Any]:
    """L1 检查：JSON 格式 + 必填字段 / L1 check: JSON format + required fields."""
    result: dict[str, Any] = {"valid": False, "errors": []}
    try:
        parsed = json.loads(output)
        for field in required_fields:
            if field not in parsed:
                result["errors"].append(f"missing field: {field}")
        result["valid"] = len(result["errors"]) == 0
        result["parsed"] = parsed
    except json.JSONDecodeError as e:
        result["errors"].append(f"JSON parse error: {e}")
    return result


def check_length(output: str, min_len: int = 10, max_len: int = 5000) -> dict[str, Any]:
    """L1 检查：输出长度 / L1 check: output length."""
    length = len(output)
    return {
        "valid": min_len <= length <= max_len,
        "length": length,
        "min": min_len,
        "max": max_len,
    }


def check_chinese_ratio(output: str, min_ratio: float = 0.3) -> dict[str, Any]:
    """L1 检查：中文占比 / L1 check: Chinese character ratio."""
    if not output:
        return {"valid": False, "ratio": 0.0}
    chinese_chars = sum(1 for c in output if "\u4e00" <= c <= "\u9fff")
    ratio = chinese_chars / len(output)
    return {"valid": ratio >= min_ratio, "ratio": round(ratio, 2)}


# ── L2 LLM-as-Judge / L2 LLM-as-Judge evaluation ──


EVAL_PROMPTS = {
    "narrative_coherence": {
        "name": "叙事连贯性 / Narrative Coherence",
        "criteria": """评估叙事文本是否：
1. 与上一轮叙事自然衔接，无突兀转折
2. 角色行为符合其性格设定
3. 情节发展逻辑合理
4. 场景描写与环境一致""",
        "scale": "1-5",
    },
    "decision_rationality": {
        "name": "决策合理性 / Decision Rationality",
        "criteria": """评估角色决策是否：
1. 符合角色性格和当前状态
2. 对当前情境做出合理反应
3. 考虑了已知信息
4. 不是随机或矛盾的行为""",
        "scale": "1-5",
    },
    "dialogue_quality": {
        "name": "对话质量 / Dialogue Quality",
        "criteria": """评估对话是否：
1. 角色口吻一致，有个性
2. 对话内容与当前情境相关
3. 对话推进了情节或揭示了角色
4. 语言自然，不像翻译腔""",
        "scale": "1-5",
    },
    "scene_richness": {
        "name": "场景丰富度 / Scene Richness",
        "criteria": """评估场景描述是否：
1. 包含视觉、听觉等多感官描写
2. 环境细节与世界观设定一致
3. 场景氛围渲染充分
4. 不过于空泛或过于冗长""",
        "scale": "1-5",
    },
}


def build_judge_prompt(
    dimension: str,
    input_text: str,
    output_text: str,
    context: str = "",
) -> str:
    """构建 LLM-as-Judge 评估提示 / Build LLM-as-Judge evaluation prompt."""
    dim = EVAL_PROMPTS.get(dimension)
    if not dim:
        return ""
    return f"""你是一个专业的游戏叙事质量评估员。请按照以下标准，对输出进行评分。

评估维度：{dim["name"]}
评分标准：
{dim["criteria"]}

评分范围：{dim["scale"]}（1=极差，5=优秀）

---输入---
{input_text}

---上下文---
{context}

---待评估输出---
{output_text}

---要求---
请直接输出 JSON 格式：
{{"score": <1-5整数>, "reason": "<简短评价>", "improvement": "<改进建议>"}}"""
