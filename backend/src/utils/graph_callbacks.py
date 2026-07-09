"""LangGraph 回调——监听 graph node / LLM 的开始/结束/错误."""

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .logging import log_graph, log_llm


class TickGraphCallback(BaseCallbackHandler):
    """全链路日志回调——自动记录顶层 Graph node + LLM 的执行耗时."""

    def __init__(self, tick: int = 0, world_id: str = "", metrics_collector=None):
        super().__init__()
        self._tick = tick
        self._world_id = world_id
        self._metrics = metrics_collector
        self._timers: dict[str, float] = {}
        self._llm_count = 0

    # ── Graph 节点 ──

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        node = _lg_node(metadata)
        if not node:
            return
        self._timers[run_id.hex[:8]] = time.monotonic()

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        cid = run_id.hex[:8]
        t0 = self._timers.pop(cid, None)
        if t0 is None:
            return
        node = _lg_node(metadata)
        if not node:
            return
        # 指标收集：记录事件类型 / Metrics: record event type
        if self._metrics:
            event_type = node.split(".")[-1] if "." in node else node
            self._metrics.record_event(self._world_id, event_type)
        log_graph(
            node,
            self._tick,
            latency_ms=round((time.monotonic() - t0) * 1000, 1),
            event="done",
            run_id=cid,
        )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        cid = run_id.hex[:8]
        t0 = self._timers.pop(cid, None)
        log_graph(
            _lg_node(metadata) or "unknown",
            self._tick,
            latency_ms=round((time.monotonic() - t0) * 1000, 1) if t0 else 0,
            event="error",
            error=str(error),
            run_id=cid,
        )

    # ── LLM 调用 ──

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        cid = run_id.hex[:8]
        self._timers[f"llm_{cid}"] = time.monotonic()
        self._llm_count += 1

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        cid = run_id.hex[:8]
        t0 = self._timers.pop(f"llm_{cid}", None)
        if t0 is None:
            return
        elapsed = time.monotonic() - t0
        log_llm(
            _lg_node(metadata) or "llm",
            "ok",
            elapsed,
            extra={
                "tick": self._tick,
                "call_n": self._llm_count,
                "run_id": cid,
                **_token_usage(response),
            },
        )
        # 指标收集：记录 LLM Token 消耗 / Metrics: record LLM token usage
        tu = _token_usage(response)
        if self._metrics and tu:
            self._metrics.record_llm(
                self._world_id,
                tu.get("tokens_in", 0),
                tu.get("tokens_out", 0),
            )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        cid = run_id.hex[:8]
        t0 = self._timers.pop(f"llm_{cid}", None)
        elapsed = time.monotonic() - t0 if t0 else 0
        log_llm(
            _lg_node(metadata) or "llm",
            "error",
            elapsed,
            extra={"tick": self._tick, "error": str(error), "run_id": cid},
        )


def _lg_node(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ""
    return metadata.get("langgraph_node", "")


def _token_usage(response: LLMResult) -> dict[str, Any]:
    try:
        if response.llm_output and "token_usage" in response.llm_output:
            tu = response.llm_output["token_usage"]
            return {
                "tokens_in": tu.get("prompt_tokens", 0),
                "tokens_out": tu.get("completion_tokens", 0),
                "tokens_total": tu.get("total_tokens", 0),
            }
    except Exception:
        logging.getLogger(__name__).debug("token_usage extraction failed", exc_info=True)
    return {}
