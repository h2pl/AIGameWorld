"""评估基类 / Evaluation base classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    """严重级别 / Severity level."""

    CRITICAL = "critical"  # P0: 世界状态已损坏
    HIGH = "high"  # P1: 影响体验，应尽快修复
    MEDIUM = "medium"  # P2: 建议优化
    LOW = "low"  # P3: 可选改进


@dataclass
class EvalIssue:
    """评估发现的问题 / Evaluation issue found."""

    dimension: str
    severity: Severity
    message: str
    detail: dict[str, Any] | None = None


@dataclass
class DimensionReport:
    """单维度评估报告 / Single dimension evaluation report."""

    dimension_name: str
    score: float  # 0-100
    passed: int
    total: int
    issues: list[EvalIssue] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not any(i.severity == Severity.CRITICAL for i in self.issues)


@dataclass
class WorldEvalReport:
    """完整世界状态评估报告 / Complete world state evaluation report."""

    tick: int
    world_id: str
    dimensions: dict[str, DimensionReport] = field(default_factory=dict)

    @property
    def overall_score(self) -> float:
        if not self.dimensions:
            return 100.0
        return sum(r.score for r in self.dimensions.values()) / len(self.dimensions)

    @property
    def is_healthy(self) -> bool:
        return all(r.healthy for r in self.dimensions.values())

    @property
    def all_issues(self) -> list[EvalIssue]:
        issues = []
        for r in self.dimensions.values():
            issues.extend(r.issues)
        return sorted(issues, key=lambda i: i.severity.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "world_id": self.world_id,
            "overall_score": round(self.overall_score, 1),
            "healthy": self.is_healthy,
            "dimensions": {
                name: {
                    "score": r.score,
                    "passed": r.passed,
                    "total": r.total,
                    "issues": [
                        {
                            "severity": i.severity.value,
                            "message": i.message,
                            "detail": i.detail,
                        }
                        for i in r.issues
                    ],
                }
                for name, r in self.dimensions.items()
            },
        }

    # LangSmith 集成格式 / LangSmith integration format
    def to_langsmith_output(self) -> str:
        """返回 LangSmith 可消费的评分输出 / Return score output consumable by LangSmith."""
        if self.is_healthy:
            return f"PASS — Score={self.overall_score:.0f}/100"
        critical = [i for i in self.all_issues if i.severity == Severity.CRITICAL]
        high = [i for i in self.all_issues if i.severity == Severity.HIGH]
        parts = [f"FAIL — Score={self.overall_score:.0f}/100"]
        if critical:
            parts.append(f"P0({len(critical)}): {'; '.join(i.message[:40] for i in critical)}")
        if high:
            parts.append(f"P1({len(high)}): {'; '.join(i.message[:40] for i in high)}")
        return "\n".join(parts)
