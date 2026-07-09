"""统一入口：调用全部 4 个维度评估器并汇总报告 / Unified entry point for all evaluators."""

import logging
from typing import Any

from .base import WorldEvalReport
from .event_causality import evaluate_event_causality
from .npc_consistency import evaluate_npc_consistency
from .rules import evaluate_game_rules
from .world_state import evaluate_world_state

logger = logging.getLogger(__name__)


class WorldStateEvaluator:
    """游戏世界状态评估器（统一入口）/ Unified game world state evaluator.

    调用各维度评估器，生成汇总报告。
    支持 LangSmith 集成：通过 to_dict() / to_langsmith_output() 返回标准格式。
    """

    def __init__(self, reflection_interval: int = 5):
        self._reflection_interval = reflection_interval

    def evaluate(
        self,
        tick: int,
        world_id: str,
        pcs: list[dict[str, Any]] | None = None,
        actors: list[dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
        scenes: list[dict[str, Any]] | None = None,
        memories: list[dict[str, Any]] | None = None,
    ) -> WorldEvalReport:
        """执行全量评估 / Run full evaluation across all dimensions."""
        logger.info("[eval] 开始评估 tick=%s world=%s", tick, world_id)

        report = WorldEvalReport(tick=tick, world_id=world_id)

        # 维度 1: 世界状态正确性 / Dimension 1: World state correctness
        report.dimensions["world_state"] = evaluate_world_state(tick, pcs, actors, events, scenes)

        # 维度 2: NPC 行为一致性 / Dimension 2: NPC consistency
        report.dimensions["npc_consistency"] = evaluate_npc_consistency(
            tick, actors, events, scenes
        )

        # 维度 3: 游戏规则合规 / Dimension 3: Game rules compliance
        report.dimensions["game_rules"] = evaluate_game_rules(tick, events, pcs, actors)

        # 维度 4: 事件因果性 + 记忆 / Dimension 4: Causality + memory
        report.dimensions["causality_memory"] = evaluate_event_causality(
            tick, events, memories, self._reflection_interval
        )

        total_issues = len(report.all_issues)
        logger.info(
            "[eval] 评估完成 tick=%s score=%.0f issues=%d dimensions=%d",
            tick,
            report.overall_score,
            total_issues,
            len(report.dimensions),
        )
        return report
