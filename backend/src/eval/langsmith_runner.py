"""LangSmith + 自研 Evaluator 桥接 / LangSmith ↔ Custom Evaluator bridge.

架构关系：
    Scenario Dataset
         │
         ▼
    LangSmith Runner
         │
         ▼
    LangGraph 运行
         │
         ▼
    自研 Evaluator (world_state / npc / rules / causality)
         │
         ▼
    Score 返回 LangSmith

LangSmith 负责：Case 管理、运行调度、展示结果、版本比较
自研 Evaluator 负责：success/score/reason 判定
"""

from __future__ import annotations

import os
from typing import Any

from src.utils.logging import get_logger

from .base import WorldEvalReport
from .world_state_evaluator import WorldStateEvaluator

logger = get_logger(__name__)


def create_langsmith_eval_config() -> dict[str, Any] | None:
    """创建 LangSmith 评估配置 / Create LangSmith evaluation config.

    仅在 LangSmith 启用时返回配置，否则返回 None。
    """
    if os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() != "true":
        return None

    return {
        "project_name": os.environ.get("LANGCHAIN_PROJECT", "aigameworld"),
        "evaluators": ["world_state", "npc_consistency", "game_rules", "causality_memory"],
    }


class LangSmithEvalResult:
    """LangSmith 评估结果 / LangSmith evaluation result.

    将自研 Evaluator 的结果转换为 LangSmith 可消费的格式。
    """

    def __init__(self, report: WorldEvalReport):
        self._report = report

    @property
    def score(self) -> float:
        """0-1 分数（LangSmith 标准）/ 0-1 score (LangSmith standard)."""
        return self._report.overall_score / 100.0

    @property
    def passed(self) -> bool:
        """是否通过 / Whether evaluation passed."""
        return self._report.is_healthy

    @property
    def reason(self) -> str:
        """评估原因说明 / Evaluation reason."""
        return self._report.to_langsmith_output()

    def to_dict(self) -> dict[str, Any]:
        """转换为 LangSmith 评分字典 / Convert to LangSmith score dict."""
        return {
            "score": self.score,
            "passed": self.passed,
            "reason": self.reason,
            "dimensions": {
                name: {
                    "score": dim.score,
                    "passed": dim.passed,
                    "total": dim.total,
                    "issues": [
                        {"severity": i.severity.value, "message": i.message} for i in dim.issues
                    ],
                }
                for name, dim in self._report.dimensions.items()
            },
        }


async def run_eval_with_langsmith(
    world_id: str,
    tick: int,
    evaluator: WorldStateEvaluator,
    pcs: list[dict[str, Any]] | None = None,
    actors: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
    scenes: list[dict[str, Any]] | None = None,
    memories: list[dict[str, Any]] | None = None,
) -> LangSmithEvalResult:
    """执行评估并返回 LangSmith 兼容结果 / Run evaluation and return LangSmith-compatible result.

    LangSmith Runner 调用此函数，获取 score 返回 LangSmith Dashboard。
    """
    report = evaluator.evaluate(
        tick=tick,
        world_id=world_id,
        pcs=pcs,
        actors=actors,
        events=events,
        scenes=scenes,
        memories=memories,
    )

    result = LangSmithEvalResult(report)

    # 如果 LangSmith 追踪已启用，将评估结果写入 LangSmith / Write to LangSmith if enabled
    if os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        try:
            from langsmith import Client

            client = Client()
            project = os.environ.get("LANGCHAIN_PROJECT", "aigameworld")

            # 创建评估 run / Create evaluation run
            client.create_run(
                name=f"world_eval_tick_{tick}",
                run_type="evaluation",
                inputs={"tick": tick, "world_id": world_id},
                outputs=result.to_dict(),
                project_name=project,
            )
            logger.info("[langsmith] 评估结果已上传: tick=%s score=%.2f", tick, result.score)
        except Exception as e:
            logger.warning("[langsmith] 上传评估结果失败: %s", e)

    return result
