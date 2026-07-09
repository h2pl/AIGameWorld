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


# ── 评估结果存储 / Evaluation result storage ──


class EvalResult:
    """单次评估结果 / Single evaluation result."""

    def __init__(
        self,
        dataset: str,
        case_id: str,
        dimension: str,
        score: float,
        reason: str = "",
        improvement: str = "",
        l1_checks: dict | None = None,
    ):
        self.dataset = dataset
        self.case_id = case_id
        self.dimension = dimension
        self.score = score
        self.reason = reason
        self.improvement = improvement
        self.l1_checks = l1_checks or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "case_id": self.case_id,
            "dimension": self.dimension,
            "score": self.score,
            "reason": self.reason,
            "improvement": self.improvement,
            "l1_checks": self.l1_checks,
        }


class EvalStore:
    """评估结果存储 / Evaluation result store.

    写入 SQLite eval_results 表，支持按 dataset/dimension 查询趋势。
    """

    def __init__(self, sqlite=None):
        self._sqlite = sqlite
        self._table_ensured = False

    async def initialize(self) -> None:
        """初始化数据库表 / Initialize database table."""
        if self._sqlite and not self._table_ensured:
            await self._ensure_table()

    async def _ensure_table(self) -> None:
        if not self._sqlite:
            return
        await self._sqlite.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_results (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset    TEXT    NOT NULL,
                case_id    TEXT    NOT NULL,
                dimension  TEXT    NOT NULL,
                score      REAL    NOT NULL,
                reason     TEXT    DEFAULT '',
                improvement TEXT    DEFAULT '',
                l1_checks  TEXT    DEFAULT '{}',
                created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_eval_dataset ON eval_results(dataset)"
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_eval_dimension ON eval_results(dimension)"
        )
        await self._sqlite.commit()
        self._table_ensured = True

    async def save(self, result: EvalResult) -> None:
        """保存评估结果 / Save evaluation result."""
        if not self._sqlite:
            return
        if not self._table_ensured:
            await self._ensure_table()
        import json as _json

        await self._sqlite.execute(
            "INSERT INTO eval_results (dataset, case_id, dimension, score, reason, improvement, l1_checks) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                result.dataset,
                result.case_id,
                result.dimension,
                result.score,
                result.reason,
                result.improvement,
                _json.dumps(result.l1_checks, ensure_ascii=False),
            ),
        )
        await self._sqlite.commit()

    async def get_recent(
        self, dataset: str = "", dimension: str = "", last_n: int = 50
    ) -> list[dict[str, Any]]:
        """获取最近 N 条评估结果 / Get recent N evaluation results."""
        if not self._sqlite:
            return []
        if not self._table_ensured:
            await self._ensure_table()
        where_parts = []
        params: list[Any] = []
        if dataset:
            where_parts.append("dataset = ?")
            params.append(dataset)
        if dimension:
            where_parts.append("dimension = ?")
            params.append(dimension)
        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
        rows = await self._sqlite.fetch_all(
            f"SELECT * FROM eval_results {where_clause} ORDER BY id DESC LIMIT ?",  # noqa: S608
            (*params, last_n),
        )
        return [dict(r) for r in rows]

    async def get_score_trend(self, dimension: str = "", last_n: int = 50) -> list[dict[str, Any]]:
        """获取评分趋势 / Get score trend."""
        if not self._sqlite:
            return []
        if not self._table_ensured:
            await self._ensure_table()
        where_clause = "WHERE dimension = ?" if dimension else ""
        params: list[Any] = [dimension] if dimension else []
        rows = await self._sqlite.fetch_all(
            f"SELECT id, dimension, score, created_at FROM eval_results "  # noqa: S608
            f"{where_clause} ORDER BY id ASC LIMIT ?",
            (*params, last_n),
        )
        return [dict(r) for r in rows]
