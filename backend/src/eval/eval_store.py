"""评估结果存储 / Evaluation result storage.

写入 SQLite eval_results 表，支持按 dataset/dimension 查询趋势。
"""

from __future__ import annotations

from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


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
