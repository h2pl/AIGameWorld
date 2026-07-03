"""LangGraph 全链路日志回调 / Full-chain logging callback for LangGraph.

组合方案：
1. BaseCallbackHandler — 监听 graph node / LLM 的开始/结束/错误
2. 集成 log_graph/log_llm — 复用现有结构化日志，带耗时
3. 支持 astream_events — debug 模式逐事件输出

只记录顶层 LangGraph 节点（metadata.langgraph_node 存在），不记录内部嵌套 chain。
Only log top-level LangGraph nodes (metadata.langgraph_node present), skip nested chains.

用法：
    config["callbacks"] = [TickGraphCallback(tick=5)]
    result = await app.ainvoke(state, config)
"""

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from ..utils.logging import get_logger
from .logging import log_graph, log_llm

logger = get_logger(__name__)


class TickGraphCallback(BaseCallbackHandler):
    """全链路日志回调——自动记录顶层 Graph node + LLM 的执行耗时."""

    def __init__(self, tick: int = 0, *, debug: bool = False):
        super().__init__()
        self._tick = tick
        self._debug = debug
        self._timers: dict[str, float] = {}
        self._llm_count = 0

    # ═══════════════════════════════════════════════════════════
    # Graph 节点 / Graph nodes
    # ═══════════════════════════════════════════════════════════

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
        """节点开始——仅记录顶层 LangGraph 节点."""
        node = _get_lg_node(metadata)
        if not node:
            return
        cid = run_id.hex[:8]
        self._timers[cid] = time.monotonic()
        if self._debug:
            log_graph(node, self._tick, latency_ms=None, event="start", run_id=cid)

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
        """节点结束——仅记录顶层 LangGraph 节点."""
        cid = run_id.hex[:8]
        t0 = self._timers.pop(cid, None)
        if t0 is None:
            return
        node = _get_lg_node(metadata)
        if not node:
            return
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        log_graph(node, self._tick, latency_ms=latency_ms, event="done", run_id=cid)

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
        """节点异常."""
        cid = run_id.hex[:8]
        t0 = self._timers.pop(cid, None)
        latency_ms = round((time.monotonic() - t0) * 1000, 1) if t0 else 0
        node = _get_lg_node(metadata) or "unknown"
        log_graph(
            node,
            self._tick,
            latency_ms=latency_ms,
            event="error",
            error=str(error),
            run_id=cid,
        )

    # ═══════════════════════════════════════════════════════════
    # LLM 调用 / LLM calls
    # ═══════════════════════════════════════════════════════════

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
        purpose = _get_lg_node(metadata) or "llm"
        log_llm(
            purpose,
            "ok",
            elapsed,
            extra={
                "tick": self._tick,
                "call_n": self._llm_count,
                "run_id": cid,
                **_extract_token_usage(response),
            },
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
        purpose = _get_lg_node(metadata) or "llm"
        log_llm(
            purpose,
            "error",
            elapsed,
            extra={"tick": self._tick, "error": str(error), "run_id": cid},
        )

    # ═══════════════════════════════════════════════════════════
    # 工具调用 / Tool calls (debug only)
    # ═══════════════════════════════════════════════════════════

    def on_tool_start(self, *args: Any, **kwargs: Any) -> None:
        if self._debug:
            cid = kwargs.get("run_id", UUID(int=0)).hex[:8]
            self._timers[cid] = time.monotonic()

    def on_tool_end(self, *args: Any, **kwargs: Any) -> None:
        if self._debug:
            cid = kwargs.get("run_id", UUID(int=0)).hex[:8]
            t0 = self._timers.pop(cid, None)
            if t0:
                log_graph(
                    "tool",
                    self._tick,
                    latency_ms=round((time.monotonic() - t0) * 1000, 1),
                    event="done",
                    run_id=cid,
                )


# ═══════════════════════════════════════════════════════════════
# 辅助函数 / Helpers
# ═══════════════════════════════════════════════════════════════


def _get_lg_node(metadata: dict[str, Any] | None) -> str:
    """从 metadata 提取 LangGraph 节点名（无则返回空字符串）."""
    if not metadata:
        return ""
    return metadata.get("langgraph_node", "")


def _extract_token_usage(response: LLMResult) -> dict[str, Any]:
    """提取 token 统计."""
    try:
        if response.llm_output and "token_usage" in response.llm_output:
            tu = response.llm_output["token_usage"]
            return {
                "tokens_in": tu.get("prompt_tokens", 0),
                "tokens_out": tu.get("completion_tokens", 0),
                "tokens_total": tu.get("total_tokens", 0),
            }
    except Exception:
        logger.debug("token_usage extraction failed", exc_info=True)
    return {}
