"""结构化日志辅助 / Structured logging helpers.

按 common-observability skill: 用 extra= 传结构化数据。
Windows 下通过 setup_logging() 强制 stdout/stderr 为 UTF-8。
"""

import contextlib
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """初始化日志 / Initialize logging with UTF-8 encoding on Windows."""
    # Windows sys.stdout 默认 cp936(GBK)，logging 中文全乱码，强制 UTF-8
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")  # pyright: ignore[reportAttributeAccessIssue]

    # 只配置 root handler，避免重复
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        h = logging.StreamHandler(sys.stderr)
        h.setLevel(level)
        h.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(name)-24s | %(levelname)-8s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root.addHandler(h)

    # 降噪——第三方库日志只显示 WARNING+
    for noisy in (
        "httpx",
        "httpcore",
        "chromadb",
        "urllib3",
        "openai",
        "langchain",
        "langchain_openai",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log_phase(phase: str, tick: int, elapsed: float | None = None, **extra) -> None:
    """记录 Graph Phase 执行 / Log Graph phase execution."""
    data = {"phase": phase, "tick": tick, **extra}
    if elapsed is not None:
        data["elapsed_ms"] = round(elapsed * 1000, 1)
    logging.getLogger("phase").info(f"[{phase}] tick={tick}", extra=data)


def log_llm(purpose: str, action: str, elapsed: float, extra: dict | None = None) -> None:
    """记录 LLM 调用 / Log LLM call."""
    data = {"purpose": purpose, "action": action, "elapsed_ms": round(elapsed * 1000, 1)}
    if extra:
        data.update(extra)
    logger = logging.getLogger("llm")
    if action == "error":
        logger.error(f"[{purpose}] 失败 / failed", extra=data)
    else:
        logger.info(f"[{purpose}] ok", extra=data)


def log_api(action: str, world_id: str, **extra) -> None:
    """记录 API 调用 / Log API call."""
    logging.getLogger("api").info(
        f"[{action}] world={world_id}", extra={"action": action, "world_id": world_id, **extra}
    )


def log_msg(op: str, tick_message_id: str, tick: int, **extra) -> None:
    """记录消息队列操作 / Log message queue operation."""
    logging.getLogger("msg").info(
        f"[{op}] id={tick_message_id} tick={tick}", extra={"op": op, "tick_message_id": tick_message_id, "tick": tick, **extra}
    )


def log_db(table: str, op: str, rows: int = 0) -> None:
    """记录 DB 操作 / Log DB operation."""
    logging.getLogger("db").info(
        f"[{table}] {op} rows={rows}", extra={"table": table, "op": op, "rows": rows}
    )


def log_graph(node: str, tick: int, **extra) -> None:
    """记录 Graph 节点 / Log Graph node execution."""
    logging.getLogger("graph").info(
        f"[graph] {node} tick={tick}", extra={"node": node, "tick": tick, **extra}
    )


def log_svc(svc: str, tick: int, **extra) -> None:
    """记录 Service 调用 / Log service call."""
    logging.getLogger("svc").info(
        f"[svc] {svc} tick={tick}", extra={"svc": svc, "tick": tick, **extra}
    )


def log_eng(eng: str, tick: int, **extra) -> None:
    """记录 Engine 调用 / Log engine call."""
    logging.getLogger("eng").info(
        f"[eng] {eng} tick={tick}", extra={"eng": eng, "tick": tick, **extra}
    )


def log_repo(repo: str, op: str, **extra) -> None:
    """记录 Repository 操作 / Log repo operation."""
    logging.getLogger("repo").info(f"[repo] {repo}.{op}", extra={"repo": repo, "op": op, **extra})
